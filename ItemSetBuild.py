from tkinter import *
from tkinter import messagebox
import tkinter as tk
import os
import datetime
import requests
import configparser
import xmltodict
import pprint
import xml.etree.ElementTree as ET

# configurations ##############################################################
config = configparser.ConfigParser()
config.read('config.ini')

apikey = config['basic']['apikey']
prefix_1 = config['basic']['set_prefix']
prefixes = prefix_1.split(",")
action_1 = config['basic']['set_action']
actions = action_1.split(",")
desc_error_1 = config['basic']['desc_error']
desc_errors = desc_error_1.split(",")


# main program ################################################################
def main(*args):
    # set_id
	set_name = gui.get_set_id()
	new_set_added = 'N'
	if set_name == "":
		gui.msgbox(set_name, "Missing Set Name")
		return
    
    #correct_date
	system_date = datetime.datetime.today()
	test_date = system_date.strftime('%Y%m%d')
	if set_name.find(test_date) == -1:
		gui.msgbox(set_name, "Missing or Incorrect Date in Set Name")
		return   
   
    # barcode
	barcode = gui.get_barcode()
	if barcode == "":
		gui.msgbox(barcode, "Bad barcode.")
		return
	gui.clear_barcode()
	
	#get set id
	set_name_search = set_name.replace(" ","_")
	x = getXML(f"https://api-na.hosted.exlibrisgroup.com/almaws/v1/conf/sets?apikey={apikey}&q=name~{set_name_search}")
	
	#parse set information
	set_xml = x.text
	set_dict = xmltodict.parse(x.text, dict_constructor=dict)
	sets_count = set_dict['sets']['@total_record_count']
	if sets_count != '0' and sets_count != '1':
		if sets_count != '1':
			set_xml = set_xml.replace("\n","")
			set_xml = set_xml.strip()
			e = ET.fromstring(set_xml)
			for set in e.findall('set'):
				if set_name == set.find('name').text:
					set_id = set.find('id').text
	elif sets_count == '0':
		new_set_added = 'Y'
		create_set_xml = \
f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<set>
<name>{set_name}</name>
<type>ITEMIZED</type>
<content>ITEM</content>
<private>false</private>
</set>
"""
		y = postXML(f"https://api-na.hosted.exlibrisgroup.com/almaws/v1/conf/sets?apikey={apikey}", create_set_xml)
		z = getXML(f"https://api-na.hosted.exlibrisgroup.com/almaws/v1/conf/sets?apikey={apikey}&q=name~{set_name}")
		new_set_xml = z.text
		set_dict = xmltodict.parse(z.text, dict_constructor=dict)
		set_id = set_dict['sets']['set']['id']
		os.mkdir(f"{set_name}")
	elif sets_count == '1':
		set_id = set_dict['sets']['set']['id']
		
    
    # get item record
	r = requests.get(f"https://api-na.hosted.exlibrisgroup.com/almaws/v1/items?item_barcode={barcode}&apikey={apikey}")
    
    # check for errors
	errors_exist = check_errors(r)
	if errors_exist[0] == True: 
		file_name = (f"unlinked_{set_name}")
		f = open(f"{set_name}\{file_name}.txt","a+")
		f.write(f"{barcode}\n")
		f.close()
		error = errors_exist[1]
		gui.msgbox(barcode, error)
		return
		finish_message = "Unlinked Item"
    
    # parse item record
	item_xml   = r.text
	item_dict  = xmltodict.parse(r.text, dict_constructor=dict) 
	title      = item_dict['item']['bib_data']['title']
	mms_id     = item_dict['item']['bib_data']['mms_id']
	holding_id = item_dict['item']['holding_data']['holding_id']
	item_pid   = item_dict['item']['item_data']['pid']
	process_status = item_dict['item']['item_data']['process_type']

	if process_status is None:
		#file_name = set_name.replace("\","")
		# add to set
		set_xml = generateSetXML(set_id, mms_id, holding_id, item_pid, barcode)
		r = postXML(f"https://api-na.hosted.exlibrisgroup.com/almaws/v1/conf/sets/{set_id}?id_type=BARCODE&op=add_members&apikey={apikey}", set_xml)
		# check for errors
		errors_exist = check_errors(r)
		if errors_exist[0] == True:
			error = errors_exist[1]
			gui.msgbox(title, error)
			return
		f = open(f"{set_name}\{set_name}.txt","a+")
		f.write(f"{barcode}\n")
		f.close()
		finish_message = "Added to Set"
	else:
		countup = len(desc_errors)
		ticks = 0
		while ticks < countup:
			compare_this = (f": '{desc_errors[ticks]}',")
			if str(compare_this) in str(process_status):
				file_name = (f"{desc_errors[ticks]}_{set_name}")
				f = open(f"{set_name}\{file_name}.txt","a+")
				f.write(f"{barcode} : {title}\n")
				f.close()
				issue_alert = (f"Item is {str(desc_errors[ticks])}")
				finish_message = (f"Item is {str(desc_errors[ticks])}")
				ticks = countup
				gui.msgbox(title, issue_alert)
				return
			else:
				ticks += 1

	gui.update_status_success(title[:60], finish_message)
            
# functions ###################################################################
def postXML(url, xml):
    headers = {'Content-Type': 'application/xml', 'charset':'UTF-8'}
    r = requests.post(url, data=xml.encode('utf-8'), headers=headers)
    return r

def getXML(url):
    headers = {'Content-Type': 'application/xml', 'charset':'UTF-8'}
    x = requests.get(url, headers=headers)
    return x

def generateSetXML(set_id, mms_id, holding_id, item_id, barcode):
    set_xml = \
f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<set>
<members>
  <member>
    <id>{barcode}</id>
  </member>
</members>
</set>"""

    return set_xml
    
def check_errors(r):
    if r.status_code != 200:
        errors = xmltodict.parse(r.text)
        error = errors['web_service_result']['errorList']['error']['errorMessage']
        return True, error
    else: 
        return False, "OK"
            
# gui #########################################################################
class gui():	
	def __init__(self, master):
		self.master = master
		master.title("Physical Item Set Builder 4")
		master.resizable(0, 0)
		master.minsize(width=600, height=100)
		master.iconbitmap("logo_small.ico")
		
		self.set_prefix_label = Label(height=1, text="Select Set Type", font="Consolas 12 bold")
		self.set_prefix_label.grid(row=0,column=0,padx="5",sticky="e")
		
		today = datetime.datetime.today()
		got_date = today.strftime('%Y%m%d')
		got_user = os.getenv('username')
		
		tkvarq = StringVar(root)
		tkvarq.set(actions[0])
		prefix_menu = OptionMenu(root, tkvarq, *actions, command=lambda x: gui.update_set_name(got_date, got_user, actions.index(tkvarq.get())))
		prefix_menu.grid(row=0,column=1,sticky='w')
		prefix_menu.config(font="Consolas 12 bold")

		self.set_added = Label(height=1, text="", font="Consolas 12 bold", fg="green")				

		self.set_label = Label(height=1, text="Name Your Set", font="Consolas 12 bold")
		self.set_label.grid(row=1, column=0, sticky='e')

		use_prefix = prefixes[0]
		default_set_name = (f"{use_prefix}_{got_date}_{got_user}")
		self.set_entry_field = Entry(font="Consolas 12 bold", width="50")
		self.set_entry_field.grid(row=1, column=1,sticky='w',padx=5)
		self.set_entry_field.insert(0, default_set_name)
		self.set_entry_field.focus()
		self.set_entry_field.bind('<Key-Return>', main)

		self.status_added = Label(height=1, text="READY", font="Consolas 12 bold", fg="green")
		self.status_added.grid(row=2,column=0)

		self.status_title = Label(height=1, text="Scan a Barcode to Start", font="Consolas 12 bold", fg="green")
		self.status_title.grid(row=2,column=1, stick='w')

		self.scan_button = Button(text="SCAN", bg="white", font="Consolas 12 bold", width="10", command=main)
		self.scan_button.grid(row=3,column=0, padx="5", pady="5")

		self.barcode_entry_field = Entry(font="Consolas 12 bold")
		self.barcode_entry_field.grid(row=3,column=1, sticky="w")
		self.barcode_entry_field.focus()
		self.barcode_entry_field.bind('<Key-Return>', main)

			
	def update_set_name(self, got_date, got_user, prefix_index):
		new_date = got_date		
		new_prefix = prefixes[prefix_index]
		new_user = got_user
		new_set_name = (f"{new_prefix}_{new_date}_{new_user}")
		self.set_entry_field.delete(0,END)
		self.set_entry_field.insert(END, new_set_name)		
		
	def msgbox(self, title, msg):
		messagebox.showerror("Attention", msg)
		gui.update_status_failure(title, msg)
        
	def get_barcode(self):
		barcode = self.barcode_entry_field.get()
		barcode = barcode.replace(" ", "")
		return barcode
 
	def get_set_id(self):
		set_id = self.set_entry_field.get()
		return set_id
 
	def clear_barcode(self):
		self.barcode_entry_field.delete(0, END)
		self.status_title.config(text="")
		self.status_added.config(text="")
            
	def update_status_success(self, title, finish_message):
		if finish_message == "Added to Set":
			color = "green"
		else:
			color = "red"
		self.status_added.config(text=finish_message, fg=color)
		self.status_title.config(text=title, fg=color)
        
	def update_status_failure(self, title, msg):
		self.status_added.config(text="")
		self.status_title.config(text=msg, fg="red")
	
	def update_set_failure(self):
		self.status_added.config(text="")
		self.status_title.config(text="SET NOT FOUND AND NOT CREATED", fg="red")
		
	
    
root = Tk()
gui = gui(root)
root.mainloop()