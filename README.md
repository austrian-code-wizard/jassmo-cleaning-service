# jassmo-cleaning-service

## Installation

- Clone this GitHub Repository
- Install Anaconda on your system (Instructions [Here](https://docs.anaconda.com/anaconda/install/))
- Make sure conda is added to your PATH by running `conda init` in your Terminal
- Navigate into the cloned repository
- Create the conda environment to run this utility with `conda env create --file conda-env.yaml`
- Activate the conda environment by running `conda activate jassmo-cleaning`


## Running

This utility reads in email files of either `.msg` or `.eml` format, parses them into JSON, collects data about the attachments and then anonymizes the email addresses by hashing them. It also uses a large international database of first and last name to check the email content against and remove human names in both body and subject. The output is a bunch of `.json` files containing the parsed emails as well as a `.csv` file containing the collected email addresses and their corresponding hashes. After running the program, you can open the `.csv` file with Excel, manually add the Role of the person for every row and then delete the column with the email addresses. You can then send the generated `.json` files and the edited `.csv` file to a third party for processing and, thus, increase the degree of anonymity of the data.

To run follow these steps:
  
- Make sure the installation steps above were completed successfully
- Within the cloned Git repository, navigate into the `jassmo_cleaning` folder.
- Call the program using `python parse_emails.py -f ../../some_input_dir -o /Users/some_user/Desktop`
- Here the `-f` flag (in this case with value `../../some_inout_dir`) must point to some folder containing the email files to be parsed. The folder can be nested and files not ending on `.eml` or `.msg` will be ignored.
- The `-o` flag specifies the output directory. The program create a new directory within this directory to save the output.