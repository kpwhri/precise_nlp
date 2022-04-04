[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]



<!-- PROJECT LOGO -->
<br />
<div>
  <p>
    <a href="https://github.com/kpwhri/precise_nlp">
      <!-- img src="images/logo.png" alt="Logo"-->
    </a>
  </p>

<h3 align="center">Precise NLP</h3>

  <p>
    Extract colorectal information from colonoscopy and pathology notes.
  </p>
</div>


<!-- TABLE OF CONTENTS -->

## Table of Contents

* [About the Project](#about-the-project)
* [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
* [Usage](#usage)
* [Roadmap](#roadmap)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)
* [Acknowledgements](#acknowledgements)

## About the Project

Extract colorectal information from colonoscopy and pathology notes.

## Getting Started

### Prerequisites

* Python 3.10 or later (3.8 or later will probably work, but not tested)
* Git (optional: you can manually download too): to download/install/update code

### Installation

* Download the code
    * Clone the library: `git clone https://github.com/kpwhri/precise_nlp`
* Create a virtual environment
    * `python -m venv .venv`
* Activate virtual environment
    * Windows: `.venv\Scripts\activate.ps1`
    * Linux: `source myvenv/bin/activate`
* Install requirements
    * `pip install .`

### Update

If not using git, delete the `precise_nlp` directory and go through steps for [Installation](#installation) again.

* Navigate to directory
    * `cd precise_nlp`
* Update with Git
    * `git pull`
* Install updated package in Virtual Environment
    * `pip install .`

## Usage

The algorithm can be run as a command-line program with a configuration file indicating which data is to be processed.
An example is provided in the `examples` directory for reading CSV files. (Complete options are listed in the json
schema in
the [`process_config` function](https://github.com/kpwhri/precise_nlp/blob/5da5389a73c650e1643c025974e1f2d28fc95013/src/precise_nlp/process.py#L444)
.)

### Configuration File

An example configuration file is provided in
the [`example` directory](https://github.com/kpwhri/precise_nlp/tree/master/example).

The two approaches are to either:

1. have all the text in a CSV, SAS7BDAT, etc., file along with an identifier
2. create a CSV file with an identifier and filenames

#### Text in File

| ID  | COLONOSCOPY_TEXT | PATHOLOGY_TEXT                 |
|-----|------------------|--------------------------------|
| 1 | Indications: ... | A) Polyp, Descending, 5mm, ... |

```yaml
data:
  filetype: csv
  path: example_data.csv
  cspy_text: COLONOSCOPY_TEXT
  path_text: PATHOLOGY_TEXT
  identifier: ID
outfile: example_data_{datetime}.out
```

#### File Mapping

| ID  | COLONOSCOPY_FILENAMAE | PATHOLOGY_FILENAME |
|-----|-----------------------|-------------------|
| 1   | FILE_0001.txt         | FILE_8371.txt     |

```yaml
data:
  filetype: csv
  path: C:\path\to\text\directory
  lookup_table: example_mapping.csv
  cspy_text: COLONOSCOPY_FILENAME
  path_text: PATHOLOGY_FILENAME
  identifier: ID
outfile: example_data_{datetime}.out
```

### Command Line/Running

* Setup
    * Navigate to directory
        * `cd precise_nlp`
    * Activate Virtual Environment:
        * Windows: `.venv\scripts\activate.ps1`
        * Linux: `source myvenv/bin/activate`
* Run
    * `python src/precise_nlp config.yaml`

## Contributing

The algorithm will likely require some modifications/enhancements to work with your particular data.

### Adding Variable

* Give it a configuration name
    * e.g., `adenoma_rectal`
* Place the configuration name in the config file under `truth`
* Add configuration name to `const.py`
* Add these along with appropriate function to `process.py#process_text`
* The function will need appropriate behavior to be useful
    * `algorithm.py`: functions called by `process_text`; these tend to access data in `path.py` and `cspy.py` and
      format the data
    * `cspy.py`: responsible for parsing the colonoscopy report and making data accessible
    * `path.py`: responsible for parsing the pathology report and making data accessible

## Versioning

The versioning system has somewhat evolved but is based on the year/month of release, along with version information
about alpha (a)/beta (b)/hotfixes (q).

`YYYYmmmV#`

e.g., the algorithm released in July 2019 would be `2019jul`, it's alpha release would be `2019julA`, the first hotfix
would be `2019julQ`, the second hotfix would be `2019julQ2`.

## Contact

Please use the [issue tracker](https://github.com/kpwhri/precise_nlp/issues).

## License

Under MIT license, see: https://kpwhri.mit-license.org/


[contributors-shield]: https://img.shields.io/github/contributors/kpwhri/precise_nlp.svg?style=flat-square

[contributors-url]: https://github.com/kpwhri/precise_nlp/graphs/contributors

[forks-shield]: https://img.shields.io/github/forks/kpwhri/precise_nlp.svg?style=flat-square

[forks-url]: https://github.com/kpwhri/precise_nlp/network/members

[stars-shield]: https://img.shields.io/github/stars/kpwhri/precise_nlp.svg?style=flat-square

[stars-url]: https://github.com/kpwhri/precise_nlp/stargazers

[issues-shield]: https://img.shields.io/github/issues/kpwhri/precise_nlp.svg?style=flat-square

[issues-url]: https://github.com/kpwhri/precise_nlp/issues

[license-shield]: https://img.shields.io/github/license/kpwhri/precise_nlp.svg?style=flat-square

[license-url]: https://kpwhri.mit-license.org/

[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat-square&logo=linkedin&colorB=555

[linkedin-url]: https://www.linkedin.com/company/kaiserpermanentewashingtonresearch