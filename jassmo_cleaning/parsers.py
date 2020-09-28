import re
import uuid
import email
import hashlib
import extract_msg
from pathlib import Path
from logging import Logger
from typing import List, Dict, Tuple
from names_dataset import NameDataset
from libratom.lib.pff import PffArchive
from email.utils import parsedate_to_datetime

logger = Logger("parser_logger")

names_dataset = NameDataset()

def parse_email_address(raw_string: str) -> str:
    if raw_string is not None:
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_string)
        if match is not None:
            return (match.group(0)).lower()
        return None
    return None

def parse_email_addresses(raw_string: str) -> List[str]:
    if raw_string is not None:
        addresses = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', raw_string)
        return [address.lower() for address in addresses]
    return []

def parse_datetime(raw_string: str) ->  str:
    if raw_string is not None and raw_string != "None":
        return parsedate_to_datetime(raw_string).isoformat()
    return None

def remove_email_address(raw_string: str) -> str:
    if raw_string is not None:
        return re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', raw_string)
    return None

def parse_msg(msg=None) -> List[Dict]:
    try:
        messages = []
        if isinstance(msg, str):
            msg = extract_msg.openMsg(msg)

        attachments = []

        for attachment in msg.attachments:
            if isinstance(attachment.data, extract_msg.message.Message):
                messages += parse_msg(attachment.data)
            elif attachment.cid is not None:
                attachments.append( {
                    "filename": attachment.longFilename,
                    "size": len(attachment.data)
                } )

        parsed_message = {
            "to": list({address for address in parse_email_addresses(msg.to)}),
            "from": parse_email_address(msg.sender),
            "recipients": list({parse_email_address(rec.email) for rec in msg.recipients}),
            "emails_in_body": list({address for address in parse_email_addresses(msg.body)}),
            "subject": msg.subject,
            "body": remove_email_address(msg.body),
            "date": parse_datetime(msg.date),
            "messageID": msg.messageId,
            "inReplyTo": msg.inReplyTo,
            "attachments": attachments
        }
        
        messages.append(parsed_message)
        return messages
    except Exception as e:
        logger.error(f"Failed to parse .msg file: {msg}. Exception: {e}")
        return None
    

def parse_eml(file_path: str) -> Dict:
    try:
        with open(file_path) as f:
            eml = email.message_from_file(f)
        
        body = ""
        attachments = []

        for part in eml.walk():
            if part.get_filename():
                attachments.append({
                    "filename": part.get_filename(),
                    "size": len(part.get_payload())
                })
            if part.get_content_type() == "text/plain":
                body += part.get_payload()

        return {
            "to": list({address for address in parse_email_addresses(eml["To"])}),
            "from": parse_email_address(eml["From"]),
            "recipients": list({address for address in parse_email_addresses(eml["CC"])}),
            "emails_in_body": list({address for address in parse_email_addresses(body)}),
            "subject": eml["Subject"],
            "body": remove_email_address(body),
            "date": parse_datetime(eml["Date"]),
            "messageID": eml["Message-ID"],
            "inReplyTo": eml["Reply-To"],
            "attachments": attachments 
        }
    except Exception as e:
        logger.error(f"Failed to parse .eml file: {file_path}. Exception: {e}")
        return None

def parse_pst(file_path: str) -> List[Dict]:
    try:
        parsed_messages = []
        archive = PffArchive(file_path)
        eml_out = Path(Path.cwd() / "tmp")

        if not eml_out.exists():
            eml_out.mkdir()

        for folder in archive.folders():
            if folder.get_number_of_sub_messages() != 0:
                for message in folder.sub_messages:
                    filename = eml_out / f"{uuid.uuid4().hex}.eml"
                    filename.write_text(re.sub("Content-Type: [ -~]*/[ -~]*;", "Content-type: text/plain;", archive.format_message(message)))
                    parsed_message = parse_eml(filename)
                    if parsed_message is not None:
                        parsed_message["attachments"] = [{"filename": attachment.name, "size": attachment.size} for attachment in archive.get_attachment_metadata(message)]
                        parsed_messages.append(parsed_message)
                    else:
                        print(f"Failed to parse converted .eml file {filename}, so cannot parse corresponding .pst")
                    filename.unlink()
        eml_out.rmdir()
        return parsed_messages
    except Exception as e:
        logger.error(f"Failed to parse .pst file: {file_path}. Exception: {e}")
        return []

def emails_to_hashes(emails: List[Dict]) -> Tuple[Dict, List]:
    email_list = {}

    for email_message in emails:
        to_list = []
        for address in email_message["to"]:
            address_hash = hashlib.sha256(address.encode()).hexdigest()
            email_list[address] = address_hash
            to_list.append(address_hash)
        email_message["to"] = to_list

        recp_list = []
        for address in email_message["recipients"]:
            address_hash = hashlib.sha256(address.encode()).hexdigest()
            email_list[address] = address_hash
            recp_list.append(address_hash)
        email_message["recipients"] = recp_list

        body_list = []
        for address in email_message["emails_in_body"]:
            address_hash = hashlib.sha256(address.encode()).hexdigest()
            email_list[address] = address_hash
            body_list.append(address_hash)
        email_message["emails_in_body"] = body_list

        if email_message["from"] is not None:
            address_hash = hashlib.sha256(email_message["from"].encode()).hexdigest()
            email_list[email_message["from"]] = address_hash
            email_message["from"] = address_hash

    return email_list, emails

def clean_word(word: str) -> str:
    return word.replace(".", "").replace(",", "").replace("!", "").replace("?", "").replace("'", "").replace('"', "")

def delete_names_from_emails(emails: List[Dict]) -> List[Dict]:
    for parsed_email in emails:
        new_body = ""
        for word in parsed_email["body"].split():
            if not names_dataset.search_first_name(clean_word(word)) and not names_dataset.search_last_name(clean_word(word)):
                new_body += f" {word}"
        parsed_email["body"] = new_body

        new_subject = ""
        for word in parsed_email["subject"].split():
            if not names_dataset.search_first_name(clean_word(word)) and not names_dataset.search_last_name(clean_word(word)):
                new_subject += f" {word}"
        parsed_email["subject"] = new_subject
    return emails