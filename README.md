
# Introduction
Extract colorectal information from colonoscopy and pathology notes.


## Adding Variable ##

* Give it a configuration name
    * e.g., `adenoma_rectal`
* Place the configuration name in the config file under `truth`
* Add configuration name to `const.py`
* Add these along with appropriate function to `process.py#process_text`
* The function will need appropriate behavior to be useful
    * `algorithm.py`: functions called by `process_text`; these tend to access data in `path.py` and `cspy.py` and format the data
    * `cspy.py`: responsible for parsing the colonoscopy report and making data accessible
    * `path.py`: responsible for parsing the pathology report and making data accessible
    

# License
Under MIT license, see: https://kpwhri.mit-license.org/

# Versioning
The versioning system has somewhat evolved but is based on the year/month of release, along with version information about alpha (a)/beta (b)/hotfixes (q).

`YYYYmmmV#`

e.g., the algorithm released in July 2019 would be `2019jul`, it's alpha release would be `2019julA`, the first hotfix would be `2019julQ`, the second hotfix would be `2019julQ2`.
