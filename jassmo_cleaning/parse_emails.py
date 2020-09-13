import sys
import json
import argparse
from os import chdir
from csv import writer, reader
from typing import List
from pathlib import Path
from datetime import datetime
from parsers import parse_eml, parse_msg, parse_pst, emails_to_hashes, delete_names_from_emails

def main(file_paths: List[str], output_path: str) -> int:
    
    output_dir = Path(output_path).absolute()

    if not output_dir.exists() or not output_dir.is_dir():
        raise ValueError(f"Output Directory does not exist: {str(output_dir.absolute())}")

    project_files = {}

    for file_path in file_paths:
        rootdir = Path(file_path).resolve()
        if not rootdir.exists() or not rootdir.is_dir() or not output_dir.exists() or not output_dir.is_dir():
            raise ValueError(f"Input Directory does not exist: {str(rootdir.absolute())}")

        project_files[rootdir.name] = [f for f in rootdir.glob('**/*') if f.is_file()]

    print(f"Parsing {len([file_path for sublist in project_files.values() for file_path in sublist])} files in {len(project_files.keys())} projects...")
    
    project_number = 1
    parsed_project_files = {}
    parsed_project_email_addresses = {}

    for project in project_files:
        parsed_emails = []
        parsed_email_number = 0

        print(f"Parsing project  {project_number} / {len(project_files.keys())}")
        project_number += 1

        for file_rel in project_files[project]:
            if str(file_rel)[-4:] == ".msg":
                parsed_emails.append(parse_msg(str(file_rel.absolute())))
            elif str(file_rel)[-4:] == ".eml":
                parsed_emails.append(parse_eml(str(file_rel.absolute())))
            elif str(file_rel)[-4:] == ".pst":
                parsed_emails += parse_pst(str(file_rel.absolute()))
            else:
                file_ending = str(file_rel).split(".")[-1]
                print(f"Invalid file type: .{file_ending}")
            parsed_email_number += 1
            if parsed_email_number % 5 == 0:
                print("--------------------")
                print(f"Parsed {(parsed_email_number/len(project_files[project])*100)}% ({parsed_email_number}/{len(project_files[project])})")

        print("--------------------")
        parsed_emails = [parsed_email for parsed_email in parsed_emails if parsed_email is not None]

        print(f"Hashing email addresses in {len(parsed_emails)} files...")
        hash_email_dict, parsed_emails = emails_to_hashes(parsed_emails)

        print("--------------------")
        print(f"Deleting human names from {len(parsed_emails)} files...")
        parsed_emails = delete_names_from_emails(parsed_emails)

        parsed_project_files[project] = parsed_emails
        parsed_project_email_addresses[project] = hash_email_dict

    chdir(output_dir)
    output_dir = output_dir.cwd() / f"email-parser-output-{datetime.utcnow().strftime('%m-%d-%Y--%H-%M-%S')}"
    output_dir.mkdir()

    for project in parsed_project_files:
        project_dir = output_dir / project
        project_dir.mkdir()

        hash_list_path = project_dir / "email-hashes.csv"
        
        print("--------------------")
        print(f"Saving {len(parsed_project_email_addresses[project])} email address-hash-pairs...")

        with open(str(hash_list_path.absolute()), "w+") as f:
            csv_writer = writer(f)
            csv_writer.writerow(["Company", "Role", "Hash"])
            for address in parsed_project_email_addresses[project]:
                csv_writer.writerow([address.split("@")[-1], "", parsed_project_email_addresses[project][address]])

        print("--------------------")
        print(f"Saving {len(parsed_project_files[project])} parsed emails to file...")

        email_index = 0
        for parsed_email in parsed_project_files[project]:
            email_path = project_dir / f"email-{email_index}.json"
            with open(str(email_path.absolute()), "w+") as f:
                f.write(json.dumps(parsed_email, indent=4))
            email_index += 1

        print("--------------------")
        print(f"Saved output to {str(output_dir / project)}")

    print("Done.")

def read_file_paths(file_list_path: str) -> List[str]:
    list_path = Path(file_list_path).absolute()

    if not list_path.exists():
        raise ValueError(f"Input file {list_path.absolute()} does not exist. Aborting.")

    if not str(list_path.absolute()).split(".")[-1] == "csv":
        raise ValueError(f"Invalid file {file_list_path.absolute()}. Must have .csv file ending.")

    with open(list_path, "r+", encoding="utf-8-sig") as f:
        file_reader = reader(f)
        return [row[0] for row in file_reader]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--file_list", required=False)
    parser.add_argument("-f", "--file_paths", required=("-c" not in sys.argv and "--file_list" not in sys.argv), nargs='+')
    parser.add_argument("-o", "--output_path", required=True)

    args = parser.parse_args()

    file_paths = []
    if args.file_list is not None:
        file_paths += read_file_paths(args.file_list)

    if args.file_paths is not None:
        file_paths += args.file_paths

    main(file_paths, args.output_path)
