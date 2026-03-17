Some guidelines for using the tool are provided below. 

## General usage 

## Flags

There are a variety of different flags available to set for the tool. 




## Config 

The config is divided into several sections. 

The section marked comparators defines the comparison-types used for different file-patterns. 
This is where tolerances for differences between the file pairs can be given, as well as your own comparison scripts provided. 

There are three further sections dedicated towards selecting which files should be included/excluded from the comparison. 

file_pairs denotes files with different names between runs that should be matched together for the comparison. 

exclude denotes files that should be ignored in the comparison, for example if there are configs/timestamps that are different between runs.  

exclude_extensions denotes entire file-types that should be ignored in the comparison. This can include time-stamped file types or ones for which a reasonable comparison metric doesn't exist (yet). 

Examples for these config files are available in comparators as yml files. 
