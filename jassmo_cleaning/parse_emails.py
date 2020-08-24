import json
import argparse
from os import chdir
from csv import writer
from pathlib import Path
from datetime import datetime
from parsers import parse_eml, parse_msg, emails_to_hashes, delete_names_from_emails

def main(file_path: str, output_path: str) -> int:
    rootdir = Path(file_path)
    output_dir = Path(output_path).absolute()

    if not rootdir.exists() or not rootdir.is_dir() or not output_dir.exists() or not output_dir.is_dir():
        raise ValueError(f"Directory does not exist: {str(rootdir.absolute())}")

    file_list = [f for f in rootdir.glob('**/*') if f.is_file()]

    print(f"Parsing {len(file_list)} files...")
    
    parsed_emails = []
    parsed_email_number = 0

    for file_rel in file_list:
        if str(file_rel)[-4:] == ".msg":
            parsed_emails.append(parse_msg(str(file_rel.absolute())))
        elif str(file_rel)[-4:] == ".eml":
            parsed_emails.append(parse_eml(str(file_rel.absolute())))
        else:
            file_ending = str(file_rel).split(".")[-1]
            print(f"Invalid file type: .{file_ending}")
        parsed_email_number += 1
        if parsed_email_number % 5 == 0:
            print("--------------------")
            print(f"Parsed {(parsed_email_number/len(file_list)*100)}% ({parsed_email_number}/{len(file_list)})")

    print("--------------------")
    parsed_emails = [parsed_email for parsed_email in parsed_emails if parsed_email is not None]

    print(f"Hashing email addresses in {len(parsed_emails)} files...")
    hash_email_dict, parsed_emails = emails_to_hashes(parsed_emails)

    print("--------------------")
    print(f"Deleting human names from {len(parsed_emails)} files...")
    parsed_emails = delete_names_from_emails(parsed_emails)

    
    chdir(output_dir)
    output_dir = output_dir.cwd() / f"email-parser-output-{datetime.utcnow().strftime('%m-%d-%Y--%H-%M-%S')}"
    output_dir.mkdir()

    hash_list_path = output_dir / "email-hashes.csv"
    
    print("--------------------")
    print(f"Saving {len(hash_email_dict)} email address - hash pairs...")

    with open(str(hash_list_path.absolute()), "w+") as f:
        csv_writer = writer(f)
        csv_writer.writerow(["Email", "Hash", "Role"])
        for address in hash_email_dict:
            csv_writer.writerow([address, hash_email_dict[address]])

    print("--------------------")
    print(f"Saving {len(parsed_emails)} parsed emails to file...")

    email_index = 0
    for parsed_email in parsed_emails:
        email_path = output_dir / f"email-{email_index}.json"
        with open(str(email_path.absolute()), "w+") as f:
            f.write(json.dumps(parsed_email, indent=4))
        email_index += 1

    print("--------------------")
    print(f"Saved output to {str(output_dir)}")
    print("Done.")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--file_path", required=True)
    parser.add_argument("-o", "--output_path", required=True)

    args = parser.parse_args()

    main(args.file_path, args.output_path)
