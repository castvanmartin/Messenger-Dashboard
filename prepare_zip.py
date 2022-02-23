from zipfile import ZipFile
import re
import os
from os.path import basename
import argparse


parser = argparse.ArgumentParser(description='Choose how many chats you want and zipfile path')
parser.add_argument("--num_of_chats", default=10)
parser.add_argument("--zip_path", required=True)
args = parser.parse_args()


if os.path.exists(args.zip_path):
	try:
		zipobj = ZipFile(args.zip_path, "r")
	except FileNotFoundError:
		print("Wrong file or path")

df = {}


for i in zipobj.infolist():
	if "message_1.json" in i.filename:
		filename = re.search("inbox/(.+?)_", i.filename)
		if filename:
			filename = filename.group(1)

		df[i.filename] = i.file_size


# Select the top n message_1.json files with the highest file size
n = int(args.num_of_chats)
smaller_df = list(sorted(df.items(), key=lambda x: x[1], reverse=True))

keys = [key[0] for key in smaller_df[0:n]]
zipobj.extractall(members=keys)


#prepare zip for upload

zipsave = ZipFile("output_zip.zip", "w")
for folder_name, subfolders, filenames in os.walk("messages/"):
	for filename in filenames:
		filepath = os.path.join(folder_name, filename)
		print(filepath)	
		zipsave.write(filepath, (filepath))

zipsave.close()