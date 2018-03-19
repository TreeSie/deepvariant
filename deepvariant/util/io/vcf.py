# Copyright 2018 Google Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Classes for reading and writing VCF files.

API for reading:
  with VcfReader(input_path) as reader:
    for variant in reader:
      process(reader.header, variant)

API for writing:
  with VcfWriter(output_path, header) as writer:
    for variant in variants:
      writer.write(variant)

where variant is a nucleus.genomics.v1.Variant protocol buffer.

If the path contains '.vcf' as an extension, then a true VCF file
will be input/output.  Otherwise, a TFRecord file will be assumed.  In either
case, an extension of '.gz' will cause the file to be treated as compressed.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function



from deepvariant.util.io import genomics_reader
from deepvariant.util.io import genomics_writer
from deepvariant.util.genomics import index_pb2
from deepvariant.util.genomics import variants_pb2
from deepvariant.util.genomics import vcf_pb2
from deepvariant.util.python import vcf_reader
from deepvariant.util.python import vcf_writer

_VCF_EXTENSIONS = frozenset(['.vcf'])


class NativeVcfReader(genomics_reader.GenomicsReader):
  """Class for reading from native VCF files.

  Most users will want to use VcfReader instead, because it dynamically
  dispatches between reading native VCF files and TFRecord files based
  on the filename's extensions.
  """

  def __init__(self, input_path, use_index=True, include_likelihoods=False):
    index_mode = index_pb2.INDEX_BASED_ON_FILENAME
    if not use_index:
      index_mode = index_pb2.DONT_USE_INDEX

    # redacted
    # list of strings.
    desired_vcf_fields = vcf_pb2.OptionalVariantFieldsToParse()
    if not include_likelihoods:
      desired_vcf_fields.exclude_genotype_quality = True
      desired_vcf_fields.exclude_genotype_likelihood = True

    self._reader = vcf_reader.VcfReader.from_file(
        input_path.encode('utf8'),
        vcf_pb2.VcfReaderOptions(
            index_mode=index_mode,
            desired_format_entries=desired_vcf_fields))

    self.header = self._reader.header

    super(NativeVcfReader, self).__init__()

  def iterate(self):
    return self._reader.iterate()

  def query(self, region):
    return self._reader.query(region)

  def __exit__(self, exit_type, exit_value, exit_traceback):
    self._reader.__exit__(exit_type, exit_value, exit_traceback)


class VcfReader(genomics_reader.DispatchingGenomicsReader):
  """Class for reading Variant protos from VCF or TFRecord files."""

  def _get_extensions(self):
    return _VCF_EXTENSIONS

  def _native_reader(self, input_path, **kwargs):
    return NativeVcfReader(input_path, **kwargs)

  def _record_proto(self):
    return variants_pb2.Variant


class NativeVcfWriter(genomics_writer.GenomicsWriter):
  """Class for writing to native VCF files.

  Most users will want VcfWriter, which will write to either native VCF
  files or TFRecords files, based on the output filename's extensions.
  """

  def __init__(self, output_path, header=None, round_qualities=False):
    """Initializer for NativeVcfWriter.

    Args:
      output_path: str. A path where we'll write our VCF file.
      header: nucleus.genomics.v1.VcfHeader. The header that defines all
        information germane to the constituent variants. This includes contigs,
        FILTER fields, INFO fields, FORMAT fields, samples, and all other
        structured and unstructured header lines.
      round_qualities: bool. If True, the QUAL field is rounded to one point
        past the decimal.
    """
    if header is None:
      header = variants_pb2.VcfHeader()
    writer_options = vcf_pb2.VcfWriterOptions(
        round_qual_values=round_qualities)
    self._writer = vcf_writer.VcfWriter.to_file(output_path, header,
                                                writer_options)
    super(NativeVcfWriter, self).__init__()

  def write(self, proto):
    self._writer.write(proto)

  def __exit__(self, exit_type, exit_value, exit_traceback):
    self._writer.__exit__(exit_type, exit_value, exit_traceback)


class VcfWriter(genomics_writer.DispatchingGenomicsWriter):
  """Class for writing Variant protos to VCF or TFRecord files."""

  def _get_extensions(self):
    return _VCF_EXTENSIONS

  def _native_writer(self, output_path, header, round_qualities=False):
    return NativeVcfWriter(
        output_path, header=header, round_qualities=round_qualities)