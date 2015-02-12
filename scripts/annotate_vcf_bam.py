import sys
import os
import argparse
import multiprocessing
import logging
import collections
import itertools
import traceback
from functools import partial
import json
import base64
import vcf
import random
import math

import pysam

def annotate_vcfs(bam, chromosomes, workdir, num_threads, vcfs):
    func_logger = logging.getLogger("%s-%s" % (annotate_vcfs.__name__, multiprocessing.current_process()))
    random.seed(0)

    # Load indexed BAM file
    sam_file = pysam.Samfile(bam.name, "rb")

    # Read through samfile and get some statistics
    # hard code this for now
    read_limit = 1000

    # this is temporary, needs to read the reference to be sensible
    num_read = 0.0
    cover_sum = 0.0
    insert_sum = 0.0
    insert_sq_sum = 0.0
    first_chr = sam_file.getrname(0)
    for i in xrange(0, read_limit):
        loc = random.randint(0, 30000000)
        alignments = sam_file.fetch(first_chr, loc, loc+1)
        if len(alignments) == 0:
            continue

        for aln in alignments:
            cover_sum += 1
            insert_sum += aln.tlen
            insert_sq_sum += aln.tlen * aln.tlen
        num_read += 1

    mean_coverage = cover_sum/num_read
    mean_insert_size = insert_sum/cover_sum
    sd_insert_size = math.sqrt((insert_sq_sum/cover_sum) - (mean_insert_size * mean_insert_size))
    func_logger.info("Estimated coverage mean: " + mean_coverage)
    func_logger.info("Estimated template size mean: " + mean_insert_size)
    func_logger.info("Estimated template size sd: " + sd_insert_size)

    # Read though VCF one line at a time
    for inVCF in vcfs:
        vcf_reader = vcf.Reader(open(inVCF))
        vcf_template_reader = vcf.Reader(open(inVCF))
        vcf_writer = vcf.Writer(open("anno_"+inVCF.name,'w'), vcf_template_reader)
        for vcf_record in vcf_reader:
            if vcf_record.CHROM not in chromosomes:
                continue

            # get the interval that corresponds to the SV
            breakpoints = (vcf_record.affected_start, vcf_record.affected_end)

            process_variant = True
            if breakpoints[1] - breakpoints[0] > 1000000:
                process_variant = False

            if process_variant:
                # get reads between breakpoints
                alignments = sam_file.fetch(vcf_record.CHROM,breakpoints[0], breakpoints[1])

                # get coverage between the breakpoints
                unique_coverage = 0
                total_coverage = 0
                for rec in alignments:
                    if rec.mapq >= 20:
                        unique_coverage += 1
                    total_coverage += 1
                vcf_record.INFO["AA_UNIQ_COV"] = unique_coverage/mean_coverage
                vcf_record.INFO["AA_TOTAL_COV"] = total_coverage/mean_coverage


            # get strand bias

            # get mapping quality stats

            # get clipped reads stats

            # get discordant reads stats

            # get supplementary alignment stats

            vcf_writer.write_record(vcf_record)

        vcf_reader.close()
        vcf_template_reader.close()
        vcf_writer.close()




if __name__ == "__main__":
    FORMAT = '%(levelname)s %(asctime)-15s %(name)-20s %(message)s'
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="Annotate VCF with additional useful features",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--bam", help="BAM file", required=True, type=file)
    parser.add_argument("--chromosomes", nargs="+", help="Chromosomes", default=[])
    parser.add_argument("--workdir", help="Working directory", default="work")
    parser.add_argument("--num_threads", help="Number of threads to use", default=1, type=int)
    parser.add_argument("--vcfs", nargs="+", help="Input VCF files", type=file)

    args = parser.parse_args()

    logger.info("Command-line: " + " ".join(sys.argv))

    annotate_vcfs(args.bam, args.chromosomes, args.workdir, args.num_threads, args.vcfs)
