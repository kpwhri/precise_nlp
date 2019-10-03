


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
    

## License
Under MIT license, see: https://kpwhri.mit-license.org/