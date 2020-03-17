# WoW Details Bot

## About this bot...

This bot get info of characters and more...

## Status
**In progress**
(In progress to change requests with python-wowapi or similars)

## Requirements
- flask
- pyTelegramBotAPI
- pymongo
- numpy

All data is stored in mLab to manage responses from each user.

## Process to use

You need to set your **Region** and **Locale*, after this point you can use the other commands

## Actual list of commands:

- help - Details and list of commands
- info - Get actual Region and Locale assigned
- region - Set or update your region
- locale - Set or update your locale
- token - Get the actual token Price
- gear - Get equipment of a character [**](#Process-to-use)
  - Example: /gear ragnaros nysler
- stats - Get all the statistics of a character  [**](#Process-to-use)
  - Example: /stats ragnaros nysler
- bg - Get Battleground statistics of a character  [**](#Process-to-use)
  - Example: /bg ragnaros nysler
- arena - Get arena statistics of a character  [**](#Process-to-use)
  - Example: /arena ragnaros nysler