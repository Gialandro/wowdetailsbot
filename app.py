"""
* @author: Gialandro
* @date: 12/03/2020
* @description: Bot to get info of World of Warcraft
"""
import sys
import os
import re
import urllib
import urllib.parse
import telebot
import pymongo
import numpy
from datetime import datetime
import json
from flask import Flask, jsonify, Response, request
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
tgTkn = os.getenv('telegramToken')
dbUri = os.getenv('dbUri')
dbName = os.getenv('dbName')
tableName = os.getenv('tableName')
tableGear = os.getenv('tableGear')
tableCovenantSkills = os.getenv('tableCovenantSkills')
tableAdmin = os.getenv('tableAdmin')
userAdmin = int(os.getenv('adminUser'))
bot = telebot.TeleBot(tgTkn, threaded=False)
pathModify = '?retryWrites=true&w=majority'
# pathModify = '?retryWrites=false'

clientId = os.getenv('blizzId')
clientSecret = os.getenv('blizzSecret')
regions = [
			'us',
			'eu',
			'kr',
			# 'tw',
			# 'cn',
			'Cancel']
locales = {
	'us': ['en_US','es_MX','pt_BR', 'Cancel'],
	'eu': ['en_GB','es_ES','fr_FR','ru_RU','de_DE','pt_PT','it_IT', 'Cancel'],
	'kr': ['ko_KR', 'Cancel']#,
	# 'tw': ['zh_TW', 'Cancel'],
	# 'cn': ['zh_CN', 'Cancel']
}

# ? Start method
@bot.message_handler(commands = ['start', 'help'])
def startMessage(message):
	bot.send_message(message.chat.id, text = '''This bot get info from World of Warcraft
	Author: @Gialandro
	Github: https://github.com/Gialandro/wowdetailsbot

	First steps:

		Set your region and locale to get data from your region and language, use this commands:

	» /region - Set or update the region of requests
		(us, eu, kr)

	» /locale - Set or update the locale of requests depending on your Region
		us = (en_US, es_MX, pt_BR)
		eu = (en_GB, es_ES, fr_FR, ru_RU, de_DE, pt_PT, it_IT)
		kr = (ko_KR)

	» /info - Get your actual Region and Locale assigned

	Whith your region and locale assigned you can use this commands:
	» /token - Get the actual token price
	» /gear [realm] [character] - Get the current gear of a character
		Example: /gear ragnaros nysler
	» /stats [realm] [character] - Get all the statistics of a character
		Example: /stats ragnaros nysler
	» /bg [realm] [character] - Get Battleground statistics of a character
		Example: /bg ragnaros nysler
	» /arena [bracket] [realm] [character] - Get bracket statistics of a character
		brackets = (2v2, 3v3, 5v5)
		Example: /arena 2v2 ragnaros nysler
	» /myth [realm] [character] - Get Mythic dungeons completed of a character
		Example: /myth ragnaros nysler
	» /dungeons - Get dungeon details of expansions
		Example: /dungeons
	» /raids - Get Mythic raid details of expansions
		Example: /raids
	» /covenant - Get details of covenants
		Example: /covenant
	''', disable_web_page_preview=True)

# ? Region method
@bot.message_handler(commands = ['region'])
def sendRegion(message):
	userId = message.from_user.id
	username = message.from_user.username
	markup = telebot.types.InlineKeyboardMarkup()
	regionList = []
	for region in regions:
		regionList.append(telebot.types.InlineKeyboardButton(text = region, callback_data = f'region:{region}-{userId}-{username}'))
	regionList = numpy.array(regionList).reshape(-1, 2)
	for item in regionList:
		markup.row(item[0], item[1])
	bot.send_message(message.chat.id, text = 'NOTE: If you change your Region you MUST assign again your Locale\nChoose a region:', reply_markup = markup)

# * Region callback
@bot.callback_query_handler(func = lambda call: re.match('^region:', call.data))
def regionHandler(call):
	req = call.data[7:]
	# ? info[0]: region
	# ? info[1]: userId
	# ? info[2]: username
	info = req.split('-')
	if info[0] != 'Cancel':
		client = pymongo.MongoClient(dbUri + pathModify)
		wowDb = client[dbName]
		wowTable = wowDb[tableName]
		bot.answer_callback_query(callback_query_id = call.id, text = 'Region selected •`_´•')
		try:
			if wowTable.count_documents({'_id': int(info[1]), 'region': {'$regex': '.{2}'}}, limit = 1):
				# ? Update process
				query = {'_id': int(info[1])}
				updateRecord = {'$set': {'region': info[0], 'locale': '', 'username': info[2]}}
				wowTable.update_one(query, updateRecord)
				bot.send_message(call.message.chat.id, 'Updated region! ※\\(^o^)/※\nNow assign your /locale')
			else:
				# ? Insert process
				wowTable.insert_one({'_id': int(info[1]), 'region': info[0], 'locale': '', 'username': info[2]})
				bot.send_message(call.message.chat.id, 'Assigned region! ※\\(^o^)/※\nNow assign your /locale')
		except Exception as e:
			showCallError(call, e)
		client.close()
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ? Locale method
@bot.message_handler(commands = ['locale'])
def sendLocale(message):
	userId = message.from_user.id
	username = message.from_user.username
	markup = telebot.types.InlineKeyboardMarkup()
	try:
		query = {'_id': userId, 'region': {'$regex': '.{2}'}}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				localeList = []
				for locale in locales.get(record.get('region')):
					localeList.append(telebot.types.InlineKeyboardButton(text = locale, callback_data = f'locale:{locale}-{userId}-{username}'))
				localeList = numpy.array(localeList).reshape(-1, 2)
				for item in localeList:
					markup.row(item[0], item[1])
				bot.send_message(message.chat.id, text = 'Choose a locale:', reply_markup = markup)
			else:
				bot.send_message(message.chat.id, 'You need assign a Region before a Locale •`_´•')
	except Exception as e:
		showError(message, e)

# * Locale callback
@bot.callback_query_handler(func = lambda call: re.match('^locale:', call.data))
def localeHandler(call):
	req = call.data[7:]
	# ? info[0]: locale
	# ? info[1]: userId
	# ? info[2]: username
	info = req.split('-')
	if info[0] != 'Cancel':
		client = pymongo.MongoClient(dbUri + pathModify)
		wowDb = client[dbName]
		wowTable = wowDb[tableName]
		bot.answer_callback_query(callback_query_id = call.id, text = 'Locale selected •`_´•')
		try:
			query = {'_id': int(info[1])}
			updateRecord = {'$set': {'locale': info[0], 'username': info[2]}}
			if wowTable.count_documents({'_id': int(info[1]), 'locale': {'$regex': '[a-z]{2}_[A-Z]{2}'}}, limit = 1):
				# ? Reassign process
				wowTable.update_one(query, updateRecord)
				bot.send_message(call.message.chat.id, 'Updated region!')
			else:
				# ? Assign process
				wowTable.update_one(query, updateRecord)
				bot.send_message(call.message.chat.id, 'Assigned region!')
		except Exception as e:
			showCallError(call, e)
		client.close()
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ? Info method
@bot.message_handler(commands = ['info'])
def sendInfo(message):
	userId = message.from_user.id
	try:
		query = {'_id': userId}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				# ? User found
				if record.get('region') != None and record.get('locale') != None:
					bot.send_message(message.chat.id, f'''Data assigned:
					Region - {record['region']}
					Locale - {record['locale']}
					''')
				# ? Info incomplete
				elif record.get('region') == None:
					bot.send_message(message.chat.id, 'Region not found')
				elif record.get('locale') == None:
					bot.send_message(message.chat.id, 'Locale not found')
			else:
				# ? User not found
				bot.send_message(message.chat.id, 'You don\'t have info assigned (´סּ︵סּ`)')
	except Exception as e:
		showError(message, e)

# ? Token Price method
@bot.message_handler(commands = ['token'])
def sendToken(message):
	userId = message.from_user.id
	try:
		query = {'_id': userId}
		result = getInfoDB(tableName, query)
		bot.send_message(message.chat.id, 'Calculating... ಠ_ರೃ')
		for record in result:
			if record.get('region') != None and record.get('locale') != None:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/data/wow/token/index'.format(record['region'])
				params = {
					'namespace': 'dynamic-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				response = response.json()
				price = str(response['price'])[:-4]
				output = '{:,}'.format(int(price))
				bot.send_message(message.chat.id, f'{output} 🌕')
			elif record.get('region') == None:
				bot.send_message(message.chat.id, 'You need assign your region')
			elif record.get('locale') == None:
				bot.send_message(message.chat.id, 'You need assign your locale')
	except requests.exceptions.ConnectionError as e:
		bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
	except Exception as e:
		showError(message, e)

# ? Character items method
@bot.message_handler(commands = ['gear'])
def sendGear(message):
	realm = None
	player = None
	if len(message.text.split()) == 3:
		realm = message.text.split()[1].lower()
		realm = realm.replace('\'', '')
		player = message.text.split()[2].lower()
		player = encodeString(player)
	userId = message.from_user.id
	breakLine = '\n'
	if realm and player:
		try:
			recordList = []
			client = pymongo.MongoClient(dbUri + pathModify)
			wowDb = client[dbName]
			wowTableGear = wowDb[tableGear]
			query = {'_id': userId}
			result = getInfoDB(tableName, query)
			bot.send_message(message.chat.id, 'Searching... ಠ_ರೃ')
			markup = telebot.types.InlineKeyboardMarkup()
			equipment = []
			for record in result:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}/equipment'.format(record['region'], realm, player)
				params = {
					'namespace': 'profile-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				statusCode = response.status_code
				response = response.json()
				if statusCode == 200:
					if response.get('equipped_items') != None:
						for item in response.get('equipped_items'):
							itemId = player + '-' + item['slot'].get('type')
							firstLine = '{} ({}){}'.format(item['name'], item['level']['display_string'], breakLine)
							itemType = ''
							if item.get('is_subclass_hidden') == None:
								itemType += '({})'.format(item['item_subclass'].get('name'))
							secondLine = '{} {} - [{}]{}{}'.format(item['inventory_type']['name'], itemType, item['quality']['name'], breakLine, breakLine)
							armor = ''
							if item.get('armor') != None:
								if item['armor'].get('display') != None:
									armor = item['armor']['display'].get('display_string')
								else:
									armor =item['armor'].get('display_string')
							durability = ''
							if item.get('durability') != None:
								durability = item['durability'].get('display_string')
							stats = ''
							if item.get('stats') != None:
								for stat in item.get('stats'):
									if stat.get('display_string') != None:
										stats += '{}{}'.format(stat.get('display_string'), breakLine)
									elif stat.get('display') != None:
										if stat.get('is_negated') == None:
											stats += '{}{}'.format(stat['display']['display_string'], breakLine)
							sockets = ''
							if item.get('sockets') != None:
								for socket in item.get('sockets'):
									if socket.get('item') != None:
										sockets += '{}: {}{}'.format(socket['item'].get('name'), socket.get('display_string'), breakLine)
							enchants = ''
							if item.get('enchantments') != None:
								for enchant in item.get('enchantments'):
									enchants += '{}{}{}'.format(breakLine, enchant.get('display_string'), breakLine)
							spells = ''
							if item.get('spells') != None:
								for spell in item.get('spells'):
									spells += '{}{} - {}{}'.format(breakLine, spell['spell'].get('name'), spell.get('description'), breakLine)
							binding = ''
							if item.get('binding') != None:
								binding += '{}{}{}'.format(item['binding'].get('name'), breakLine, breakLine)
							azeriteDetails = ''
							if item.get('azerite_details') != None:
								if item['azerite_details'].get('selected_essences') != None:
									essences = item['azerite_details'].get('selected_essences')
									azeriteDetails += 'Skills:{}'.format(breakLine)
									for essence in essences:
										if essence.get('main_spell_tooltip') != None:
											azeriteDetails += '- Act: {}{}'.format(essence['main_spell_tooltip']['spell'].get('name'), breakLine)
										elif essence.get('passive_spell_tooltip') != None:
											azeriteDetails += '- Pas: {}{}'.format(essence['passive_spell_tooltip']['spell'].get('name'), breakLine)
								azeriteDetails += '{}'.format(breakLine)
							lastLine = ''
							if armor != '':
								lastLine += armor
							if durability != '':
								lastLine += '{}{}'.format(breakLine, durability)
							itemData = firstLine + secondLine
							if stats != '':
								itemData += stats
							if enchants != '':
								itemData += enchants
							if sockets != '':
								itemData += sockets
							if spells != '':
								itemData += spells
							if binding != '':
								itemData += binding
							if azeriteDetails != '':
								itemData += azeriteDetails
							if lastLine != '':
								itemData += lastLine
							gearQuery = {'item': itemId}
							itemRecord = {
								'$set': {
									'user': userId,
									'item': itemId,
									'data': itemData
								}
							}
							recordList.append(pymongo.UpdateOne(gearQuery, itemRecord, upsert=True))
							equipment.append(telebot.types.InlineKeyboardButton(text = item['inventory_type']['name'] + itemType, callback_data = 'gear:' + itemId))
						getProfilePic(record.get('region'), record.get('locale'), realm, player, blizzSession.get('access_token'), message.chat.id)
						# * Show 2 buttons per row
						if len(equipment) % 2 != 0:
							equipment.append(1)
						equipment = numpy.array(equipment).reshape(-1, 2)
						for item in equipment:
							if item[1] != 1:
								markup.row(item[0], item[1])
							else:
								markup.row(item[0], telebot.types.InlineKeyboardButton(text = 'Close', callback_data = 'gear:close'))
						# ! Player summary structure
						urlSummary = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}'.format(record['region'], realm, player)
						summaryResponse = requests.get(urlSummary, params = params)
						summaryStatus = summaryResponse.status_code
						summaryResponse = summaryResponse.json()
						if summaryStatus == 200:
							summaryData = ''
							if summaryResponse['faction'].get('type') == 'HORDE':
								summaryData += '⚔️ {}\n'.format(summaryResponse['faction'].get('name'))
							else:
								summaryData += '🦁 {}\n'.format(summaryResponse['faction'].get('name'))
							if summaryResponse.get('active_title') != None:
								nameWithTitle = summaryResponse['active_title'].get('display_string').format(name = summaryResponse.get('name')) + '\n'
							else:
								nameWithTitle = '{}\n'.format(summaryResponse.get('name'))
							summaryData += nameWithTitle
							summaryData += 'Lvl: {}\n'.format(summaryResponse.get('level'))
							summaryData += '{}\n'.format(summaryResponse['race'].get('name'))
							summaryData += '{}: {}\n'.format(summaryResponse['character_class'].get('name'), summaryResponse['active_spec'].get('name'))
							if summaryResponse.get('guild') != None:
								summaryData += '<{}> {}\n'.format(summaryResponse['guild'].get('name'), summaryResponse['realm'].get('name'))
							else:
								summaryData += '{}\n'.format(summaryResponse['realm'].get('name'))
							lastLogin = int(summaryResponse.get('last_login_timestamp'))/1000
							lastLogin = datetime.fromtimestamp(lastLogin)
							summaryData += 'Last login: {}\n'.format(lastLogin)
							summaryData += 'iLvl: {}\n'.format(summaryResponse.get('equipped_item_level'))
							summaryData += 'Equipped items: {}'.format(len(response['equipped_items']))
							bot.send_message(message.chat.id, text = summaryData, reply_markup = markup)
						# * Send result and buttons
						else:
							bot.send_message(message.chat.id, text = 'Player: {}\nRealm: {}\nEquiped items: {}'.format(player.capitalize(), realm.capitalize(), len(response['equipped_items'])), reply_markup = markup)
						wowTableGear.bulk_write(recordList)
					else:
						bot.send_message(message.chat.id, f'{player.capitalize()} has no equipment ¯\\_(ツ)_/¯')
				else:
					bot.send_message(message.chat.id, 'Player not found ☉ ‿ ⚆')
		except requests.exceptions.ConnectionError as e:
			bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
		except Exception as e:
			showError(message, e)
		client.close()
	else :
		bot.send_message(message.chat.id, 'You need specify a realm and player •`_´•')

# * Character item callback
@bot.callback_query_handler(func = lambda call: re.match('^gear:', call.data))
def gearHandler(call):
	gear = call.data[5:]
	if gear != 'close':
		client = pymongo.MongoClient(dbUri)
		bot.answer_callback_query(callback_query_id = call.id, text = 'Option accepted •`_´•')
		try:
			query = {'item': gear}
			result = getInfoDB(tableGear, query)
			for record in result:
				if record:
					# ? Gear found
					if record.get('data') != None:
						result = record.get('data')
						bot.send_message(call.message.chat.id, result)
					# ? Gear without data
					else:
						bot.send_message(call.message.chat.id, 'Data not found (´סּ︵סּ`)')
				else:
					# ? Gear not found
					bot.send_message(call.message.chat.id, 'Item not found (´סּ︵סּ`)')
		except Exception as e:
			showCallError(call, e)
		client.close()
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ? Character stats method
@bot.message_handler(commands = ['stats'])
def sendStats(message):
	realm = None
	player = None
	if len(message.text.split()) == 3:
		realm = message.text.split()[1].lower()
		realm = realm.replace('\'', '')
		player = message.text.split()[2].lower()
		player = encodeString(player)
	userId = message.from_user.id
	if realm and player:
		try:
			query = {'_id': userId}
			result = getInfoDB(tableName, query)
			bot.send_message(message.chat.id, 'Searching... ಠ_ರೃ')
			for record in result:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}/statistics'.format(record['region'], realm, player)
				params = {
					'namespace': 'profile-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				statusCode = response.status_code
				response = response.json()
				if statusCode == 200:
					# ! Profile image
					getProfilePic(record.get('region'), record.get('locale'), realm, player, blizzSession.get('access_token'), message.chat.id)
					# ! Player summary structure
					urlSummary = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}'.format(record['region'], realm, player)
					summaryResponse = requests.get(urlSummary, params = params)
					summaryStatus = summaryResponse.status_code
					summaryResponse = summaryResponse.json()
					summaryData = ''
					if summaryStatus != 404:
						if summaryResponse['faction'].get('type') == 'HORDE':
							summaryData += '⚔️ {}\n'.format(summaryResponse['faction'].get('name'))
						else:
							summaryData += '🦁 {}\n'.format(summaryResponse['faction'].get('name'))
						if summaryResponse.get('active_title') != None:
							nameWithTitle = summaryResponse['active_title'].get('display_string').format(name = summaryResponse.get('name')) + '\n'
						else:
							nameWithTitle = '{}\n'.format(summaryResponse.get('name'))
						summaryData += nameWithTitle
						summaryData += 'Lvl: {}\n'.format(summaryResponse.get('level'))
						summaryData += '{}\n'.format(summaryResponse['race'].get('name'))
						summaryData += '{}: {}\n'.format(summaryResponse['character_class'].get('name'), summaryResponse['active_spec'].get('name'))
						if summaryResponse.get('guild') != None:
							summaryData += '<{}> {}\n'.format(summaryResponse['guild'].get('name'), summaryResponse['realm'].get('name'))
						else:
							summaryData += '{}\n'.format(summaryResponse['realm'].get('name'))
						lastLogin = int(summaryResponse.get('last_login_timestamp'))/1000
						lastLogin = datetime.fromtimestamp(lastLogin)
						summaryData += 'Last login: {}\n'.format(lastLogin)
						summaryData += 'iLvl: {}\n\n'.format(summaryResponse.get('equipped_item_level'))
					# ! Stats
					health = '{:,}'.format(int(response.get('health')))
					summaryData += 'Health: {}\n'.format(health)
					powerType = '{:,}'.format(int(response.get('power')))
					summaryData += '{}: {}\n'.format(response['power_type'].get('name'), powerType)
					if response['speed'].get('rating') != 0:
						speed = '{:,}'.format(int(response['speed'].get('rating')))
						summaryData += 'Speed: {}\n'.format(speed)
					strength = '{:,}'.format(int(response['strength'].get('effective')))
					summaryData += 'Strength: {}\n'.format(strength)
					agility = '{:,}'.format(int(response['agility'].get('effective')))
					summaryData += 'Agility: {}\n'.format(agility)
					intellect = '{:,}'.format(int(response['intellect'].get('effective')))
					summaryData += 'Intellect: {}\n'.format(intellect)
					stamina = '{:,}'.format(int(response['stamina'].get('effective')))
					summaryData += 'Stamina: {}\n'.format(stamina)
					bonusArmor = '{:,}'.format(int(response.get('bonus_armor')))
					summaryData += 'Bonus armor: {}\n'.format(bonusArmor)
					versatility = '{:,}'.format(int(response.get('versatility')))
					summaryData += 'Versatility: {}\n'.format(versatility)
					attackPower = '{:,}'.format(int(response.get('attack_power')))
					summaryData += 'Attack power: {}\n'.format(attackPower)
					armor = '{:,}'.format(int(response['armor'].get('effective')))
					summaryData += 'Armor: {}\n'.format(armor)
					# ! Bonus stats
					meleeCrit = '{0:.2f}%'.format(response['melee_crit'].get('value'))
					meleeCritRating = '{:,}'.format(int(response['melee_crit'].get('rating')))
					summaryData += 'Melee crit: {} | rating: {}\n'.format(meleeCrit, meleeCritRating)
					meleeHaste = '{0:.2f}%'.format(response['melee_haste'].get('value'))
					meleeHasteRating = '{:,}'.format(int(response['melee_haste'].get('rating')))
					summaryData += 'Melee haste: {} | rating: {}\n'.format(meleeHaste, meleeHasteRating)
					mastery = '{0:.2f}%'.format(response['mastery'].get('value'))
					masteryRating = '{:,}'.format(int(response['mastery'].get('rating')))
					summaryData += 'Mastery: {} | rating: {}\n'.format(mastery, masteryRating)
					if response['lifesteal'].get('value') != 0:
						lifesteal = '{0:.2f}%'.format(response['lifesteal'].get('value'))
						lifestealRating = '{:,}'.format(int(response['lifesteal'].get('rating')))
						summaryData += 'Lifesteal: {} | rating: {}\n'.format(lifesteal, lifestealRating)
					if response['power_type'].get('id') == 0:
						spellPower = '{:,}'.format(int(response.get('spell_power')))
						summaryData += 'Spell power: {}\n'.format(spellPower)
						spellPenetration = '{:,}'.format(int(response.get('spell_penetration')))
						summaryData += 'Spell penetration: {}\n'.format(spellPenetration)
						spellCrit = '{0:.2f}%'.format(response['spell_crit'].get('value'))
						spellCritRating = '{:,}'.format(int(response['spell_crit'].get('rating')))
						summaryData += 'Spell crit: {} | rating: {}\n'.format(spellCrit, spellCritRating)
						manaRegen = '{:,}'.format(int(response.get('mana_regen')))
						summaryData += 'Mana regen: {}\n'.format(manaRegen)
					if response['dodge'].get('value') != 0:
						dodge = '{0:.2f}%'.format(response['dodge'].get('value'))
						dodgeRating = '{:,}'.format(int(response['dodge'].get('rating')))
						summaryData += 'Dodge: {} | rating: {}\n'.format(dodge, dodgeRating)
					if response['parry'].get('value') != 0:
						parry = '{0:.2f}%'.format(response['parry'].get('value'))
						parryRating = '{:,}'.format(int(response['parry'].get('rating')))
						summaryData += 'Parry: {} | rating: {}\n'.format(parry, parryRating)
					if response['block'].get('value') != 0:
						block = '{0:.2f}%'.format(response['block'].get('value'))
						blockRating = '{:,}'.format(int(response['block'].get('rating')))
						summaryData += 'Block: {} | rating: {}\n'.format(block, blockRating)
					rangedCrit = '{0:.2f}%'.format(response['ranged_crit'].get('value'))
					rangedCritRating = '{:,}'.format(int(response['ranged_crit'].get('rating')))
					summaryData += 'Ranged Crit: {} | rating: {}\n'.format(rangedCrit, rangedCritRating)
					rangedHaste = '{0:.2f}%'.format(response['ranged_haste'].get('value'))
					rangedHasteRating = '{:,}'.format(int(response['ranged_haste'].get('rating')))
					summaryData += 'Ranged Haste: {} | rating: {}\n'.format(rangedHaste, rangedHasteRating)
					if response['power_type'].get('id') == 0:
						spellHaste = '{0:.2f}%'.format(response['spell_haste'].get('value'))
						spellHasteRating = '{:,}'.format(int(response['spell_haste'].get('rating')))
						summaryData += 'Spell haste: {} | rating: {}\n'.format(spellHaste, spellHasteRating)
					if response.get('corruption') != None:
						summaryData += 'Corruption: {}'.format(response['corruption'].get('effective_corruption'))
					bot.send_message(message.chat.id, text = summaryData)
				else:
					bot.send_message(message.chat.id, 'Player not found ☉ ‿ ⚆')
		except requests.exceptions.ConnectionError as e:
			bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
		except Exception as e:
			showError(message, e)
	else :
		bot.send_message(message.chat.id, 'You need specify a realm and player •`_´•')

# ? Character BG stats method
@bot.message_handler(commands = ['bg'])
def sendBGStats(message):
	realm = None
	player = None
	if len(message.text.split()) == 3:
		realm = message.text.split()[1].lower()
		realm = realm.replace('\'', '')
		player = message.text.split()[2].lower()
		player = encodeString(player)
	userId = message.from_user.id
	if realm and player:
		try:
			query = {'_id': userId}
			result = getInfoDB(tableName, query)
			bot.send_message(message.chat.id, 'Searching... ಠ_ರೃ')
			for record in result:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}/pvp-summary'.format(record['region'], realm, player)
				params = {
					'namespace': 'profile-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				statusCode = response.status_code
				response = response.json()
				if statusCode == 200:
					# ! Profile image
					getProfilePic(record.get('region'), record.get('locale'), realm, player, blizzSession.get('access_token'), message.chat.id)
					character = response.get('character')
					bgData = ''
					bgData += '{} - {}\n'.format(character.get('name'), character['realm'].get('name'))
					bgData += 'Honor lvl: {}\nHonorable kills: {}\n\n'.format(response.get('honor_level'), response.get('honorable_kills'))
					maps = response.get('pvp_map_statistics')
					if maps != None:
						for pvpMap in maps:
							bgData += 'Map: {}\n'.format(pvpMap['world_map'].get('name'))
							stats = pvpMap.get('match_statistics')
							bgData += 'Played: {}\nWon: {}\nLost: {}\n\n'.format(stats.get('played'), stats.get('won'), stats.get('lost'))
					bot.send_message(message.chat.id, text = bgData)
				else:
					bot.send_message(message.chat.id, 'Player not found ☉ ‿ ⚆')
		except requests.exceptions.ConnectionError as e:
			bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
		except Exception as e:
			showError(message, e)
	else:
		bot.send_message(message.chat.id, 'You need specify a realm and player •`_´•')

# ? Character arena stats method
@bot.message_handler(commands = ['arena'])
def sendArenaStats(message):
	bracket = None
	realm = None
	player = None
	if len(message.text.split()) == 4:
		bracket = message.text.split()[1].lower()
		realm = message.text.split()[2].lower()
		realm = realm.replace('\'', '')
		player = message.text.split()[3].lower()
		player = encodeString(player)
	userId = message.from_user.id
	if realm and player and bracket:
		try:
			query = {'_id': userId}
			result = getInfoDB(tableName, query)
			bot.send_message(message.chat.id, 'Searching... ಠ_ರೃ')
			for record in result:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}/pvp-bracket/{}'.format(record['region'], realm, player, bracket)
				params = {
					'namespace': 'profile-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				statusCode = response.status_code
				response = response.json()
				if statusCode == 200 and statusCode != 403:
					# ! Profile image
					getProfilePic(record.get('region'), record.get('locale'), realm, player, blizzSession.get('access_token'), message.chat.id)
					arenaData = ''
					faction = response.get('faction')
					character = response.get('character')
					season = response.get('season_match_statistics')
					weekly = response.get('weekly_match_statistics')
					if faction.get('type') == 'HORDE':
						arenaData += '⚔️ {}\n'.format(faction.get('name'))
					elif faction.get('type') == 'ALLIANCE':
						arenaData += '🦁 {}\n'.format(faction.get('name'))
					arenaData += '{} - {}\n\n'.format(character.get('name'), character['realm'].get('name'))
					arenaData += 'Season stats:\nPlayed: {}\nWon: {}\nLost: {}\n\n'.format(season.get('played'), season.get('won'), season.get('lost'))
					arenaData += 'Weekly stats:\nPlayed: {}\nWon: {}\nLost: {}\n\n'.format(weekly.get('played'), weekly.get('won'), weekly.get('lost'))
					bot.send_message(message.chat.id, text = arenaData)
				else:
					bot.send_message(message.chat.id, 'No result ☉ ‿ ⚆')
		except requests.exceptions.ConnectionError as e:
			bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
		except Exception as e:
			showError(message, e)
	else:
		bot.send_message(message.chat.id, 'You need specify a realm, player and bracket •`_´•')

# ? Character mythic keystone runs method
@bot.message_handler(commands=['myth'])
def sendMythicKeystone(message):
	realm = None
	player = None
	if len(message.text.split()) == 3:
		realm = message.text.split()[1].lower()
		realm = realm.replace('\'', '')
		player = message.text.split()[2].lower()
		player = encodeString(player)
	userId = message.from_user.id
	if realm and player:
		try:
			query = {'_id': userId}
			result = getInfoDB(tableName, query)
			bot.send_message(message.chat.id, 'Searching... ಠ_ರೃ')
			for record in result:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}/mythic-keystone-profile'.format(record['region'], realm, player)
				params = {
					'namespace': 'profile-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				statusCode = response.status_code
				response = response.json()
				if statusCode == 200 and statusCode != 403:
					# ! Profile image
					getProfilePic(record.get('region'), record.get('locale'), realm, player, blizzSession.get('access_token'), message.chat.id)
					mythicData = ''
					if response.get('character') != None:
						player = response.get('character')
						mythicData += '{} - {}\n'.format(player.get('name'), player['realm'].get('name'))
					if response.get('seasons') != None:
						seasons = response.get('seasons')
						for season in seasons:
							mythicData += 'Season: {}\n'.format(season.get('id'))
					if response['current_period'].get('best_runs') != None:
						mythicData += 'Mythics:\n'
						dungeons = response['current_period'].get('best_runs')
						for dungeon in dungeons:
							mythicData += '\n{} - Mythic +{}\n'.format(dungeon['dungeon'].get('name'), dungeon.get('keystone_level'))
							mythicData += 'Duration: {}\n'.format(sendDuration(dungeon.get('duration')))
							lastRun = int(dungeon.get('completed_timestamp')) / 1000
							lastRun = datetime.fromtimestamp(lastRun)
							mythicData += 'Last run: {}\n'.format(lastRun)
							mythicData += 'Completed within time: {}\n'.format(dungeon.get('is_completed_within_time'))
							if dungeon.get('keystone_affixes') != None:
								mythicData += 'Affixes:\n'
								affixes = dungeon.get('keystone_affixes')
								for affixe in affixes:
									mythicData += '- {}\n'.format(affixe.get('name'))
					else:
						mythicData += '\nNo mythics found this week ☉ ‿ ⚆'
					bot.send_message(message.chat.id, mythicData)
				else:
					bot.send_message(message.chat.id, 'No result ☉ ‿ ⚆')
		except requests.exceptions.ConnectionError as e:
			bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
		except Exception as e:
			showError(message, e)
	else:
		bot.send_message(message.chat.id, 'You need specify a realm and player •`_´•')

# ? Expansions Encounters method (Dungeons and raids)
@bot.message_handler(commands=['dungeons', 'raids'])
def sendExpansions(message):
	userId = message.from_user.id
	markup = telebot.types.InlineKeyboardMarkup()
	try:
		query = {'_id': userId}
		result = getInfoDB(tableName, query)
		for record in result:
			if record.get('region') != None and record.get('locale') != None:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/data/wow/journal-expansion/index'.format(record['region'])
				params = {
					'namespace': 'static-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				response = response.json()
				response = response.get('tiers')
				for exp in response:
					markup.add(telebot.types.InlineKeyboardButton(text = '{}'.format(exp.get('name')), callback_data = 'exp:{}-{}-{}'.format(exp.get('id'), userId, message.text[1:])))
				markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='exp:Cancel'))
				bot.send_message(message.chat.id, text = 'Choose an Expansion:', reply_markup = markup)
			elif record.get('region') == None:
				bot.send_message(message.chat.id, 'You need assign your region')
			elif record.get('locale') == None:
				bot.send_message(message.chat.id, 'You need assign your locale')
	except requests.exceptions.ConnectionError as e:
		bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
	except Exception as e:
		showError(message, e)

# # * Dungeons callback
@bot.callback_query_handler(func = lambda call: re.match('^exp:', call.data))
def dungeonHandler(call):
	req = call.data[4:]
	# ? info[0]: expansion
	# ? info[1]: userId
	# ? info[2]: command
	info = req.split('-')
	markup = telebot.types.InlineKeyboardMarkup()
	if info[0] != 'Cancel':
		query = {'_id': int(info[1])}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				# ? User found
				if record.get('region') != None and record.get('locale') != None:
					blizzSession = createAccessToken(record['region'])
					try:
						url = 'https://{}.api.blizzard.com/data/wow/journal-expansion/{}'.format(record.get('region'), info[0])
						params = {
							'namespace': 'static-{}'.format(record.get('region')),
							'locale': record.get('locale'),
							'access_token': blizzSession['access_token']
						}
						response = requests.get(url, params = params)
						response = response.json()
						if response.get('dungeons') != None and info[2] == 'dungeons':
							for dungeon in response.get('dungeons'):
								markup.add(telebot.types.InlineKeyboardButton(text = '{}'.format(dungeon.get('name')), callback_data = 'instance:{}-{}'.format(dungeon.get('id'), info[1])))
							markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='dungeon:Cancel'))
						elif response.get('raids') != None and info[2] == 'raids':
							for dungeon in response.get('raids'):
								markup.add(telebot.types.InlineKeyboardButton(text = '{}'.format(dungeon.get('name')), callback_data = 'instance:{}-{}'.format(dungeon.get('id'), info[1])))
							markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='dungeon:Cancel'))
						bot.send_message(chat_id = call.message.chat.id, text = '» {}'.format(response.get('name')), reply_markup = markup)
					except requests.exceptions.ConnectionError as e:
						bot.send_message(call.message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
					except Exception as e:
						showCallError(call, e)
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# * Instance list callback
@bot.callback_query_handler(func = lambda call: re.match('^instance:', call.data))
def instanceSelectionHandler(call):
	req = call.data[9:]
	# ? info[0]: dungeonId
	# ? info[1]: userId
	info = req.split('-')
	markup = telebot.types.InlineKeyboardMarkup()
	if info[0] != 'Cancel':
		query = {'_id': int(info[1])}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				# ? User found
				if record.get('region') != None and record.get('locale') != None:
					blizzSession = createAccessToken(record['region'])
					try:
						getInstancePic(record.get('region'), record.get('locale'), info[0], blizzSession['access_token'], call.message.chat.id)
						url = 'https://{}.api.blizzard.com/data/wow/journal-instance/{}'.format(record.get('region'), info[0])
						params = {
							'namespace': 'static-{}'.format(record.get('region')),
							'locale': record.get('locale'),
							'access_token': blizzSession['access_token']
						}
						response = requests.get(url, params = params)
						response = response.json()
						data = ''
						if response.get('name') != None:
							data += '»» {}\n'.format(response.get('name'))
						if response.get('location') != None:
							data += 'Location» {}\n\n'.format(response['location'].get('name'))
						if response.get('description') != None:
							data += '{}'.format(response.get('description'))
						if response.get('encounters') != None:
							for boss in response.get('encounters'):
								markup.add(telebot.types.InlineKeyboardButton(text = '{}'.format(boss.get('name')), callback_data = 'boss:{}-{}'.format(boss.get('id'), info[1])))
							markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='boss:Cancel'))
						bot.send_message(chat_id = call.message.chat.id, text = data, reply_markup = markup)
					except requests.exceptions.ConnectionError as e:
						bot.send_message(call.message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
					except Exception as e:
						showCallError(call, e)
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# * Boss list callback
@bot.callback_query_handler(func = lambda call: re.match('^boss:', call.data))
def bossSelectionHandler(call):
	req = call.data[5:]
	# ? info[0]: bossId
	# ? info[1]: userId
	info = req.split('-')
	markup = telebot.types.InlineKeyboardMarkup()
	if info[0] != 'Cancel':
		query = {'_id': int(info[1])}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				# ? User found
				if record.get('region') != None and record.get('locale') != None:
					blizzSession = createAccessToken(record['region'])
					try:
						url = 'https://{}.api.blizzard.com/data/wow/journal-encounter/{}'.format(record.get('region'), info[0])
						params = {
							'namespace': 'static-{}'.format(record.get('region')),
							'locale': record.get('locale'),
							'access_token': blizzSession['access_token']
						}
						response = requests.get(url, params = params)
						response = response.json()
						if response.get('creatures') != None:
							for boss in response.get('creatures'):
								bot.send_message(call.message.chat.id, boss.get('name'))
								getBossPic(record.get('region'), record.get('locale'), boss['creature_display'].get('id'), blizzSession['access_token'], call.message.chat.id)
						data = ''
						if response.get('name') != None:
							data += '»»» {}\n'.format(response.get('name'))
						if response.get('description') != None:
							data += '📖 {}\n'.format(response.get('description'))
						if response.get('sections') != None:
							resumen = response['sections'][0]
							data += '\n🔴 {}\n{}\n'.format(resumen.get('title'), resumen.get('body_text'))
							if resumen.get('sections') != None:
								for index, detail in enumerate(resumen.get('sections')):
									if detail.get('title') == 'Tanques' or detail.get('title') == 'Tanque' or detail.get('title') == 'Tanks' or detail.get('title') == 'Tank':
										data += '\n🛡'
									elif detail.get('title') == 'Infligidores de daño' or detail.get('title') == 'Damage Dealers' or detail.get('title') == 'DPS':
										data += '\n🧨'
									elif detail.get('title') == 'Sanadores' or detail.get('title') == 'Sanador' or detail.get('title') == 'Healers' or detail.get('title') == 'Healer':
										data += '\n🚑'
									data += '{}\n{}\n'.format(detail.get('title'), detail.get('body_text').replace('$bullet;', '»'))
						if response.get('items') != None:
							data += 'Objects:'
							for item in response.get('items'):
								markup.add(telebot.types.InlineKeyboardButton(text = '{}'.format(item['item'].get('name')), callback_data = 'item:{}-{}'.format(item['item'].get('id'), info[1])))
							markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='item:Cancel'))
						bot.send_message(chat_id = call.message.chat.id, text = data, reply_markup = markup)
					except requests.exceptions.ConnectionError as e:
						bot.send_message(call.message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
					except Exception as e:
						showCallError(call, e)
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# * Item list callback
@bot.callback_query_handler(func = lambda call: re.match('^item:', call.data))
def itemSelectionHandler(call):
	req = call.data[5:]
	# ? info[0]: itemId
	# ? info[1]: userId
	info = req.split('-')
	if info[0] != 'Cancel':
		query = {'_id': int(info[1])}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				# ? User found
				if record.get('region') != None and record.get('locale') != None:
					blizzSession = createAccessToken(record['region'])
					try:
						getItemPic(record.get('region'), record.get('locale'), info[0], blizzSession['access_token'], call.message.chat.id)
						url = 'https://{}.api.blizzard.com/data/wow/item/{}'.format(record.get('region'), info[0])
						params = {
							'namespace': 'static-{}'.format(record.get('region')),
							'locale': record.get('locale'),
							'access_token': blizzSession['access_token']
						}
						response = requests.get(url, params = params)
						response = response.json()
						data = ''
						if response.get('name') != None:
							data += '»»»» {} - {}\n'.format(response.get('name'), response['quality'].get('name'))
						if response['preview_item'].get('level') != None:
							data += '{}\n'.format(response['preview_item']['level'].get('display_string'))
						if response['item_subclass'].get('name') != None:
							data += '{}\n'.format(response['item_subclass'].get('name'))
						if response['preview_item'].get('stats') != None:
							for stat in response['preview_item'].get('stats'):
								data += '{}\n'.format(stat['display'].get('display_string'))
						if response['preview_item'].get('spells') != None:
							for stat in response['preview_item'].get('spells'):
								data += '{}\n'.format(stat.get('description'))
						bot.send_message(chat_id = call.message.chat.id, text = data)
					except requests.exceptions.ConnectionError as e:
						bot.send_message(call.message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
					except Exception as e:
						showCallError(call, e)
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# ? Covenant method
@bot.message_handler(commands=['covenant'])
def sendCovenants(message):
	userId = message.from_user.id
	markup = telebot.types.InlineKeyboardMarkup()
	try:
		query = {'_id': userId}
		result = getInfoDB(tableName, query)
		for record in result:
			if record.get('region') != None and record.get('locale') != None:
				blizzSession = createAccessToken(record['region'])
				url = 'https://{}.api.blizzard.com/data/wow/covenant/index'.format(record['region'])
				params = {
					'namespace': 'static-{}'.format(record['region']),
					'locale': record['locale'],
					'access_token': blizzSession['access_token']
				}
				response = requests.get(url, params = params)
				response = response.json()
				response = response.get('covenants')
				for covenant in response:
					markup.add(telebot.types.InlineKeyboardButton(text = '{}'.format(covenant.get('name')), callback_data = 'cov:{}-{}-{}'.format(covenant.get('id'), userId, message.text[1:])))
				markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='cov:Cancel'))
				bot.send_message(message.chat.id, text = 'Choose a Covenant:', reply_markup = markup)
			elif record.get('region') == None:
				bot.send_message(message.chat.id, 'You need assign your region')
			elif record.get('locale') == None:
				bot.send_message(message.chat.id, 'You need assign your locale')
	except requests.exceptions.ConnectionError as e:
		bot.send_message(message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
	except Exception as e:
		showError(message, e)

# # * Covenant callback
@bot.callback_query_handler(func = lambda call: re.match('^cov:', call.data))
def covenantHandler(call):
	req = call.data[4:]
	# ? info[0]: expansion
	# ? info[1]: userId
	# ? info[2]: command
	info = req.split('-')
	markup = telebot.types.InlineKeyboardMarkup()
	if info[0] != 'Cancel':
		query = {'_id': int(info[1])}
		result = getInfoDB(tableName, query)
		for record in result:
			if record:
				# ? User found
				if record.get('region') != None and record.get('locale') != None:
					blizzSession = createAccessToken(record['region'])
					try:
						data = ''
						url = 'https://{}.api.blizzard.com/data/wow/covenant/{}'.format(record.get('region'), info[0])
						params = {
							'namespace': 'static-{}'.format(record.get('region')),
							'locale': record.get('locale'),
							'access_token': blizzSession['access_token']
						}
						response = requests.get(url, params = params)
						statusCode = response.status_code
						response = response.json()
						if statusCode == 200:
							getCovenantPic(record.get('region'), record.get('locale'), response.get('id'), blizzSession['access_token'], call.message.chat.id)
							recordList = []
							client = pymongo.MongoClient(dbUri + pathModify)
							wowDb = client[dbName]
							wowTableCovenant = wowDb[tableCovenantSkills]
							if response.get('name') != None:
								data += '» {}\n'.format(response.get('name'))
							if response.get('description') != None:
								data += '📖{}\n'.format(response.get('description'))
							if response.get('signature_ability') != None:
								data += '\n»» 💫{}:\n{}\n'.format(response['signature_ability']['spell_tooltip']['spell'].get('name'), response['signature_ability']['spell_tooltip'].get('description'))
							if response['signature_ability']['spell_tooltip'].get('cooldown') != None:
								data += '» {}\n'.format(response['signature_ability']['spell_tooltip'].get('cooldown'))
							if response['signature_ability']['spell_tooltip'].get('cast_time') != None:
								data += '» {}'.format(response['signature_ability']['spell_tooltip'].get('cast_time'))
							bot.send_message(chat_id = call.message.chat.id, text = data)
							if response.get('class_abilities') != None:
								skillList = []
								for skill in response.get('class_abilities'):
									skillData = ''
									classSkill = '{}-{}'.format(response.get('name'), skill['playable_class'].get('name'))
									skillList.append(telebot.types.InlineKeyboardButton(text = '{}'.format(skill['playable_class'].get('name')), callback_data = f'covSkill:{classSkill}'))
									skillData = '» {}\n»» {}\n» {}\n» {}\n'.format(skill['playable_class'].get('name'), skill['spell_tooltip']['spell'].get('name'), skill['spell_tooltip'].get('description'), skill['spell_tooltip'].get('cast_time'))
									if skill['spell_tooltip'].get('cooldown') != None and skill['spell_tooltip'].get('cooldown') != 'None':
										skillData += '» {}\n'.format(skill['spell_tooltip'].get('cooldown'))
									if skill['spell_tooltip'].get('power_cost') != None and skill['spell_tooltip'].get('power_cost') != 'None':
										skillData += '» {}'.format(skill['spell_tooltip'].get('power_cost'))
									skillQuery = {'classSkill': classSkill}
									itemRecord = {
										'$set': {
											'classSkill': classSkill,
											'data': skillData
										}
									}
									recordList.append(pymongo.UpdateOne(skillQuery, itemRecord, upsert=True))
								skillList = numpy.array(skillList).reshape(-1, 2)
								for item in skillList:
									markup.row(item[0], item[1])
								markup.add(telebot.types.InlineKeyboardButton(text='Cancel', callback_data='covSkill:Cancel'))
								bot.send_message(chat_id = call.message.chat.id, text = 'Choocse a class:', reply_markup = markup)
							wowTableCovenant.bulk_write(recordList)
						else:
							bot.send_message(call.message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
					except requests.exceptions.ConnectionError as e:
						bot.send_message(call.message.chat.id, 'Error connecting to Blizzard... try later (҂◡_◡) ᕤ')
					except Exception as e:
						showCallError(call, e)
	else:
		bot.send_message(call.message.chat.id, 'Operation cancelled (ㆆ _ ㆆ)')
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

# * Covenant skill callback
@bot.callback_query_handler(func = lambda call: re.match('^covSkill:', call.data))
def covenantSkillHandler(call):
	covenant = call.data[9:]
	if covenant != 'close':
		client = pymongo.MongoClient(dbUri)
		bot.answer_callback_query(callback_query_id = call.id, text = 'Option accepted •`_´•')
		try:
			query = {'classSkill': covenant}
			result = getInfoDB(tableCovenantSkills, query)
			for record in result:
				if record:
					# ? covenant found
					if record.get('data') != None:
						result = record.get('data')
						bot.send_message(call.message.chat.id, result)
					# ? covenant without data
					else:
						bot.send_message(call.message.chat.id, 'Skill not found (´סּ︵סּ`)')
				else:
					# ? covenant not found
					bot.send_message(call.message.chat.id, 'Skill not found (´סּ︵סּ`)')
		except Exception as e:
			showCallError(call, e)
		client.close()
	bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)

@bot.message_handler(commands = ['data'])
def sendAdminData(message):
	bot.send_message(message.chat.id, 'Searching Data... ಠ_ರೃ')
	if message.from_user.id == userAdmin:
		try:
			query = {}
			result = getInfoDB(tableAdmin, query)
			totalRecords = 0
			for record in result:
				msg = 'Id: {}\nRegion: {}\nLocale: {}\nUsername: {}\n'.format(record.get('_id'), record.get('region'), record.get('locale'), record.get('username'))
				totalRecords += 1
				bot.send_message(message.chat.id, msg)
			bot.send_message(message.chat.id, f'{totalRecords} records founds (◕ᴥ◕ʋ)')
		except Exception as e:
			showError(message, e)
	else:
		bot.send_message(message.chat.id, 'You are not the admin •`_´•')

def createAccessToken(region):
	url = "https://{}.battle.net/oauth/token".format(region)
	body = {
		"grant_type": 'client_credentials'
	}
	auth = HTTPBasicAuth(clientId, clientSecret)
	response = requests.post(url, data = body, auth = auth)
	return response.json()

def getProfilePic(region, locale, realm, player, token, chatId):
	path = 'https://{}.api.blizzard.com/profile/wow/character/{}/{}/character-media'.format(region, realm, player.lower())
	params = {
		'namespace': 'profile-{}'.format(region),
		'locale': locale,
		'access_token': token
	}
	response = requests.get(path, params = params)
	status = response.status_code
	response = response.json()
	if status == 200:
		try:
			if response.get('assets') != None:
				response = response.get('assets')
				response = response[2].get('value')
			elif response.get('render_url') != None:
				response = response.get('render_url')
			bot.send_chat_action(chatId, 'upload_photo')
			bot.send_photo(chatId, response)
		except:
			bot.send_message(chatId, text = 'Profile image not found ¯\\_(ツ)_/¯')
	else:
		bot.send_message(chatId, text = 'Profile image not found ¯\\_(ツ)_/¯')

def getInstancePic(region, locale, instanceId, token, chatId):
	path = 'https://{}.api.blizzard.com/data/wow/media/journal-instance/{}'.format(region, instanceId)
	params = {
		'namespace': 'static-{}'.format(region),
		'locale': locale,
		'access_token': token
	}
	response = requests.get(path, params = params)
	status = response.status_code
	response = response.json()
	if status == 200:
		try:
			if response.get('assets') != None:
				response = response.get('assets')
				response = response[0].get('value')
			bot.send_chat_action(chatId, 'upload_photo')
			bot.send_photo(chatId, response)
		except:
			bot.send_message(chatId, text = 'Instance image not found ¯\\_(ツ)_/¯')
	else:
		bot.send_message(chatId, text = 'Instance image not found ¯\\_(ツ)_/¯')

def getBossPic(region, locale, instanceId, token, chatId):
	path = 'https://{}.api.blizzard.com/data/wow/media/creature-display/{}'.format(region, instanceId)
	params = {
		'namespace': 'static-{}'.format(region),
		'locale': locale,
		'access_token': token
	}
	response = requests.get(path, params = params)
	status = response.status_code
	response = response.json()
	if status == 200:
		try:
			if response.get('assets') != None:
				response = response.get('assets')
				response = response[0].get('value')
			bot.send_chat_action(chatId, 'upload_photo')
			bot.send_photo(chatId, response)
		except:
			bot.send_message(chatId, text = 'Boss image not found ¯\\_(ツ)_/¯')
	else:
		bot.send_message(chatId, text = 'Boss image not found ¯\\_(ツ)_/¯')

def getItemPic(region, locale, itemId, token, chatId):
	path = 'https://{}.api.blizzard.com/data/wow/media/item/{}'.format(region, itemId)
	params = {
		'namespace': 'static-{}'.format(region),
		'locale': locale,
		'access_token': token
	}
	response = requests.get(path, params = params)
	status = response.status_code
	response = response.json()
	if status == 200:
		try:
			if response.get('assets') != None:
				response = response.get('assets')
				response = response[0].get('value')
			bot.send_chat_action(chatId, 'upload_photo')
			bot.send_photo(chatId, response)
		except:
			bot.send_message(chatId, text = 'Item image not found ¯\\_(ツ)_/¯')
	else:
		bot.send_message(chatId, text = 'Item image not found ¯\\_(ツ)_/¯')

def getCovenantPic(region, locale, itemId, token, chatId):
	path = 'https://{}.api.blizzard.com/data/wow/media/covenant/{}'.format(region, itemId)
	params = {
		'namespace': 'static-{}'.format(region),
		'locale': locale,
		'access_token': token
	}
	response = requests.get(path, params = params)
	status = response.status_code
	response = response.json()
	if status == 200:
		try:
			if response.get('assets') != None:
				response = response.get('assets')
				response = response[0].get('value')
			bot.send_chat_action(chatId, 'upload_photo')
			bot.send_photo(chatId, response)
		except:
			bot.send_message(chatId, text = 'Covenant image not found ¯\\_(ツ)_/¯')
	else:
		bot.send_message(chatId, text = 'Covenant image not found ¯\\_(ツ)_/¯')

def encodeString(infoToEncode):
	infoToEncode = infoToEncode.lower()
	infoToEncode = urllib.parse.quote(infoToEncode, encoding = None, safe = '')
	return infoToEncode

def showError(message, error):
	if message.from_user.id == userAdmin:
		trace_back = sys.exc_info()[2]
		line = trace_back.tb_lineno
		bot.send_message(message.chat.id, f'({type(error)}): {error} - {line}')
	bot.send_message(message.chat.id, f'¯\\_(ツ)_/¯ Error... ({type(error)}): {error}')

def showCallError(call, error):
	if call.message.from_user.id == userAdmin:
		trace_back = sys.exc_info()[2]
		line = trace_back.tb_lineno
		bot.send_message(call.message.chat.id, f'({type(error)}): {error} - {line}')
	bot.send_message(call.message.chat.id, f'¯\\_(ツ)_/¯ Error... ({type(error)}): {error}')

def getInfoDB(tableName, query):
	client = pymongo.MongoClient(dbUri)
	wowDb = client[dbName]
	wowTable = wowDb[tableName]
	result = wowTable.find(query)
	client.close()
	return result

def sendDuration(millisTime):
	duration = ''
	millis = int(millisTime)
	seconds = (millis / 1000) % 60
	seconds = int(seconds)
	minutes = (millis / (1000 * 60)) % 60
	minutes = int(minutes)
	hours = (millis / (1000 * 60 * 60)) % 24
	if hours < 1:
		duration = '{}m {}s'.format(minutes, seconds)
	else:
		duration = '{}h {}m {}s'.format(hours, minutes, seconds)
	return duration

@app.route('/bot', methods = ['GET', 'POST'])
def getMessage():
	if request.method == "POST":
		bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
	return jsonify({'status': 'ok'})

if __name__ == '__main__':
	app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
