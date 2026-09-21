# Data access and layout

Raw datasets are never committed. Put authorized local data under `data/raw/`
or link to it there. Normalized manifests in `data/manifests/` record source
versions, filenames, sizes, and available checksums.

## JIGSAWS

JIGSAWS is access controlled for academic research. Request it through the
[official JIGSAWS page](https://cirl.lcsr.jhu.edu/research/hmm/datasets/jigsaws_release/)
and comply with its agreement. In this checkout, `data/raw/jigsaws` points to
the existing paper-1 copy at `/Users/hahnyu/Documents/surgical-skill/data`.

## Public external datasets

- ROSMA: [Zenodo record 7100542](https://zenodo.org/records/7100542), CC BY 4.0.
- BGU-SKILLS: [DOI 10.17617/3.CYSIAP](https://doi.org/10.17617/3.CYSIAP), CC BY 4.0.
- BGU-PatCut: [DOI 10.17617/3.JK4ANF](https://doi.org/10.17617/3.JK4ANF), CC BY 4.0.

Phase 1 inspected repository metadata and the smallest necessary documentation
files. Large public archives were not copied into this repository.

