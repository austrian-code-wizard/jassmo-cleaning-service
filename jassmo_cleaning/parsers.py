import re
import uuid
import pypff
import email
import hashlib
import extract_msg
from pathlib import Path
from logging import Logger
from typing import List, Dict, Tuple
from names_dataset import NameDataset
from email.utils import parsedate_to_datetime

logger = Logger("parser_logger")

names_dataset = NameDataset()

def parse_email_address(raw_string: str) -> str:
    if raw_string is not None:
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', raw_string)
        if match is not None:
            return (match.group(0)).lower()
        return ""
    return ""

def parse_email_addresses(raw_string: str) -> List[str]:
    if raw_string is not None:
        addresses = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', raw_string)
        return [address.lower() for address in addresses]
    return []

def parse_datetime(raw_string: str) ->  str:
    if raw_string is not None and raw_string != "None":
        return parsedate_to_datetime(raw_string).isoformat()
    return ""

def remove_email_address(raw_string: str) -> str:
    if raw_string is not None:
        return re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', raw_string)
    return ""

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
            "subject": msg.subject if msg.subject is not None else "",
            "body": remove_email_address(msg.body),
            "date": parse_datetime(msg.date),
            "messageID": msg.messageId if msg.messageId is not None else "",
            "inReplyTo": msg.inReplyTo if msg.inReplyTo is not None else "",
            "attachments": attachments
        }
        
        messages.append(parsed_message)
        return messages
    except Exception as e:
        logger.error(f"Failed to parse .msg file: {msg}. Exception: {e}")
        return []
    

def parse_eml(file_path: str) -> Dict:
    try:
        with open(file_path, encoding="utf-8") as f:
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
            "subject": eml["Subject"] if eml["Subject"] is not None else "",
            "body": remove_email_address(body),
            "date": parse_datetime(eml["Date"]),
            "messageID": eml["Message-ID"] if eml["Message-ID"] is not None else "",
            "inReplyTo": eml["Reply-To"] if eml["Reply-To"] is not None else "",
            "attachments": attachments 
        }
    except Exception as e:
        logger.error(f"Failed to parse .eml file: {file_path}. Exception: {e}")
        return None

def recurse_pst(base: pypff.folder):
    messages = []
    for folder in base.sub_folders:
        if folder.number_of_sub_folders:
            messages += recurse_pst(folder)
        for msg in folder.sub_messages:
            try:
                message = {
                    "to": [],
                    "from": "",
                    "recipients": [],
                    "emails_in_body": list({address for address in parse_email_addresses(msg.plain_text_body.decode())}),
                    "subject": msg.subject if msg.subject is not None else "",
                    "body": remove_email_address(msg.plain_text_body.decode()),
                    "date": "",
                    "messageID": "",
                    "inReplyTo": "",
                    "attachments": [] 
                }
                for header in msg.get_transport_headers().splitlines():
                    header = header.strip().lower()
                    if header.startswith("from:"):
                        message["from"] = parse_email_address(header)
                    elif header.startswith("to:"):
                        message["to"] = list({address for address in parse_email_addresses(header)})
                    elif header.startswith("cc:"):
                        message["recipients"] = list({address for address in parse_email_addresses(header)})
                    elif header.startswith("date:"):
                        message["date"] = parse_datetime(header.split("date:")[-1].strip())
                    elif header.startswith("message-id:"):
                        message["messageID"] = header.split("message-id:")[-1].strip()
                    elif header.startswith("reply-to:"):
                        message["inReplyTo"] = header.split("reply-to:")[-1].strip()
                for attachment in msg.attachments:
                    message["attachments"].append({
                        "filename": attachment.name,
                        "size": attachment.size
                    })
                messages.append(message)
            except Exception as e:
                logger.error(f"Failed to parse message in .pst file. Message subject: {msg.subject} Exception: {e}")
    return messages


def parse_pst(file_path: str) -> List[Dict]:
    try:
        pst = pypff.open(file_path)
        root = pst.get_root_folder()
        return recurse_pst(root)
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

def delete_phone_numbers_from_emails(emails: List[Dict]) -> List[Dict]:
    for parsed_email in emails:
        parsed_email["body"] = re.sub(r"\+?\d+(?:[- \)]+\d+)+", "", parsed_email["body"])
    return emails

def clean_unique_emails(emails: List[str]) -> List[str]:
    # pylint does not realize that "email" in the list comprehension here is a string, so you can ignore it if it shows any warnings
    return list(set([email for email in emails if sum([1 for char in email if char.isdigit()]) <= 2]))
