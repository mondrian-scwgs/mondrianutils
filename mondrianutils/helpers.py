'''
Created on Feb 19, 2018

@author: dgrewal
'''
import errno
import gzip
import logging
import os
import subprocess
import tarfile
from subprocess import Popen, PIPE

import pandas as pd


def run_cmd(cmd, output=None):
    stdout = PIPE
    if output:
        stdout = open(output, "w")

    p = Popen(cmd, stdout=stdout, stderr=PIPE)

    cmdout, cmderr = p.communicate()
    retc = p.returncode

    if retc:
        raise Exception(
            "command failed. stderr:{}, stdout:{}".format(
                cmdout,
                cmderr))

    if output:
        stdout.close()

    print(cmdout)
    print(cmderr)


class getFileHandle(object):
    def __init__(self, filename, mode='rt'):
        self.filename = filename
        self.mode = mode

    def __enter__(self):
        if self.get_file_format(self.filename) in ["csv", 'plain-text']:
            self.handle = open(self.filename, self.mode)
        elif self.get_file_format(self.filename) == "gzip":
            self.handle = gzip.open(self.filename, self.mode)
        elif self.get_file_format(self.filename) == "h5":
            self.handle = pd.HDFStore(self.filename, self.mode)
        return self.handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.handle.close()

    def get_file_format(self, filepath):
        if filepath.endswith('.tmp'):
            filepath = filepath[:-4]

        _, ext = os.path.splitext(filepath)

        if ext == ".csv":
            return "csv"
        elif ext == ".gz":
            return "gzip"
        elif ext == ".h5" or ext == ".hdf5":
            return "h5"
        elif ext == '.yaml':
            return 'plain-text'
        else:
            logging.getLogger("single_cell.helpers").warning(
                "Couldn't detect output format. extension {}".format(ext)
            )
            return "plain-text"


def makedirs(directory, isfile=False):
    if isfile:
        directory = os.path.dirname(directory)
        if not directory:
            return

    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def build_shell_script(command, tag, tempdir):
    outfile = os.path.join(tempdir, "{}.sh".format(tag))
    with open(outfile, 'w') as scriptfile:
        scriptfile.write("#!/bin/bash\n")
        if isinstance(command, list) or isinstance(command, tuple):
            command = ' '.join(map(str, command)) + '\n'
        scriptfile.write(command)
    return outfile


def run_in_gnu_parallel(commands, tempdir, ncores):
    makedirs(tempdir)

    scriptfiles = []

    for tag, command in enumerate(commands):
        scriptfiles.append(build_shell_script(command, tag, tempdir))

    parallel_outfile = os.path.join(tempdir, "commands.txt")
    with open(parallel_outfile, 'w') as outfile:
        for scriptfile in scriptfiles:
            outfile.write("sh {}\n".format(scriptfile))

    subprocess.run(['parallel', '--jobs', str(ncores)], stdin=open(parallel_outfile))


def make_tarfile(output_filename, source_dir):
    assert output_filename.endswith('.tar.gz')

    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def validate_outputs(files, name, samples=[]):
    if 'metadata.yaml' in files:
        files.remove('metadata.yaml')

    if name == 'hmmcopy':
        expected_files = [
            'hmmcopy_params.csv.gz', 'hmmcopy_params.csv.gz.yaml',
            'hmmcopy_segments.csv.gz', 'hmmcopy_segments.csv.gz.yaml',
            'hmmcopy_reads.csv.gz', 'hmmcopy_reads.csv.gz.yaml',
            'hmmcopy_metrics.csv.gz', 'hmmcopy_metrics.csv.gz.yaml',
            'hmmcopy_segments_pass.tar.gz', 'hmmcopy_segments_fail.tar.gz',
            'hmmcopy_heatmap.pdf', 'input.json'
        ]
        assert sorted(files) == sorted(expected_files)
    elif name == 'alignment':
        expected_files = [
            'alignment_gc_metrics.csv.gz', 'alignment_gc_metrics.csv.gz.yaml', 'alignment_metrics.csv.gz',
            'alignment_metrics.csv.gz.yaml', 'alignment_metrics.tar.gz', 'all_cells_bulk.bam', 'all_cells_bulk.bam.bai',
            'all_cells_bulk_contaminated.bam', 'all_cells_bulk_contaminated.bam.bai', 'all_cells_bulk_control.bam',
            'all_cells_bulk_control.bam.bai', 'detailed_fastqscreen_breakdown.csv.gz',
            'detailed_fastqscreen_breakdown.csv.gz.yaml', 'input.json'
        ]
        assert sorted(files) == sorted(expected_files)
    elif name == 'breakpoint_calling':
        expected_files = ['four_way_consensus.csv.gz','four_way_consensus.csv.gz.yaml',
                          'input.json']
        for sample in samples:
            expected_files += [
                '{}_breakpoint_library_table.csv'.format(sample),
                '{}_breakpoint_table.csv'.format(sample),
                '{}_gridss.vcf.gz'.format(sample),
                '{}_lumpy.vcf'.format(sample),
                '{}.svaba.somatic.sv.vcf.gz'.format(sample)
            ]
        assert sorted(files) == sorted(expected_files)
    elif name == 'variant_calling':
        expected_files = [
            'final_maf_all_samples.maf',
            'final_vcf_all_samples.vcf.gz',
            'final_vcf_all_samples.vcf.gz.csi',
            'final_vcf_all_samples.vcf.gz.tbi',
        ]
        for sample in samples:
            expected_files += [
                '{}_consensus.vcf.gz'.format(sample),
                '{}_consensus.vcf.gz.csi'.format(sample),
                '{}_consensus.vcf.gz.tbi'.format(sample),
                '{}_museq.vcf.gz'.format(sample),
                '{}_museq.vcf.gz.csi'.format(sample),
                '{}_museq.vcf.gz.tbi'.format(sample),
                '{}_mutect.vcf.gz'.format(sample),
                '{}_mutect.vcf.gz.csi'.format(sample),
                '{}_mutect.vcf.gz.tbi'.format(sample),
                '{}_strelka_indel.vcf.gz'.format(sample),
                '{}_strelka_indel.vcf.gz.csi'.format(sample),
                '{}_strelka_indel.vcf.gz.tbi'.format(sample),
                '{}_strelka_snv.vcf.gz'.format(sample),
                '{}_strelka_snv.vcf.gz.csi'.format(sample),
                '{}_strelka_snv.vcf.gz.tbi'.format(sample),
                '{}_updated_counts.maf'.format(sample)
            ]
        assert sorted(files) == sorted(expected_files)
    elif name == 'snv_genotyping':
        expected_files = ['snv_genotyping.csv.gz', 'snv_genotyping.csv.gz.yaml']
        assert sorted(files) == sorted(expected_files)
    else:
        raise NotImplementedError()
