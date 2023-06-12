import requests, threading, re, json, time, humanize, textwrap, math, os
from discord_webhook import DiscordWebhook
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

background = Image.open('images/item.png').convert("RGBA")
rolimonsICO = Image.open('images/rolimons.png').convert("RGBA")
robloxICO = Image.open('images/roblox.png').convert("RGBA")
font = ImageFont.truetype('fonts/GothamBold.otf', size=16)
fontBig = ImageFont.truetype('fonts/Gotham.otf', size=20)
fontSmall = ImageFont.truetype('fonts/Gotham.otf', size=16)
tradeBackground = Image.open('images/background.png').convert("RGBA")
lock = threading.Lock()

with open('config.json','r') as config:
    config = json.load(config)

try: os.mkdir('limiteds')
except: pass

class Player:
    def __init__(self):
        self.ignore_trades = []
        self.webhook = DiscordWebhook(url=config['discordWebhook'], username="Inbound Notifier")

        self.session = requests.Session()
        self.session.cookies['.ROBLOSECURITY'] = config['cookie']
        self.username = self.session.get(
            'https://www.roblox.com/my/settings/json'
        ).json()['Name']

        self.rolimons()
        self.collectImages()
        time.sleep(1)
        threading.Thread(target=self.looping).start()

    def rolimons(self):
        self.itemData = json.loads(
            re.search('item_details = (.*?);', requests.get('https://www.rolimons.com/itemtable').text).group(1)
        )
        self.otherItemData = requests.get(
            'https://www.rolimons.com/itemapi/itemdetails'
        ).json()['items']

    def downloadImages(self, _list):
        for data in _list:
            assetId = data['requestId']
            imageUrl = data['imageUrl']
            response = requests.get(
                imageUrl
            )
            with open(f'limiteds/{assetId}.png', 'wb') as file:
                file.write(response.content)

    def collectImages(self):
        ignore = []
        for a, b, c in os.walk('limiteds'):
            for file in c:
                ignore.append(str(file).split('.png')[0])

        items = [i for i in self.itemData if i not in ignore]
        if len(items):
            print(f'Downloading {len(items)} limited images, check your limiteds folder')
        for i in range(math.ceil(len(items)/100)):
            currentIds = items[i*100 : (i+1)*100]
            payload = []
            for id in currentIds:
                payload.append(
                    {
                        "requestId": str(id),
                        "targetId": int(id),
                        "type": "Asset",
                        "size": "110x110",
                        "format": "Png"
                    }
                )

            while 1:
                try:
                    response = self.session.post(
                        f'https://thumbnails.roblox.com/v1/batch', timeout = 6,
                        json = payload
                    )
                    if response.status_code == 200:
                        data = response.json()
                        threads = [threading.Thread(target=self.downloadImages, args=[data['data'][i::25]]) for i in range(25)]
                        for t in threads: t.start()
                        for t in threads: t.join()
                        break
                except:
                    pass

    def getOldInbounds(self):
        response = self.session.get(
            'https://trades.roblox.com/v1/trades/inbound?cursor=&limit=25&sortOrder=Desc'
        )
        self.ignore_trades = [inbound['id'] for inbound in response.json()['data']]

    def getInbounds(self):
        while True:
            try:
                response = self.session.get(
                    'https://trades.roblox.com/v1/trades/inbound?cursor=&limit=25&sortOrder=Desc'
                )
                if response.status_code == 200:
                    currentInbounds = response.json()['data']
                    for inbound in currentInbounds:
                        if inbound['id'] not in self.ignore_trades:
                            self.checkValuation(inbound['id'])

            except Exception as err:
                print(err)
                pass

    def checkValuation(self, tradeId):
        while 1:
            try:
                response = self.session.get(
                    f'https://trades.roblox.com/v1/trades/{tradeId}'
                )
                if response.status_code == 200:
                    r = response.json()
                    myValue = theirValue = myRap = theirRap = 0
                    myOffer, theirOffer = [], []
                    myRobux, theirRobux = r["offers"][0]["robux"], r["offers"][1]["robux"]

                    for item in r['offers'][0]['userAssets']:
                        assetId = str(item['assetId'])
                        itemValue, itemRap, itemName, itemProjection, itemPrice = self.otherItemData[assetId][4], self.otherItemData[assetId][2], self.itemData[assetId][0], self.itemData[assetId][19], self.itemData[assetId][5]
                        myOffer.append(self.importLimited(item['assetId'], int(itemRap), int(itemValue), itemName, itemProjection, itemPrice))
                        myValue += int(itemValue)
                        myRap += int(itemRap)

                    for item in r['offers'][1]['userAssets']:
                        assetId = str(item['assetId'])
                        itemValue, itemRap, itemName, itemProjection, itemPrice = self.otherItemData[assetId][4], self.otherItemData[assetId][2], self.itemData[assetId][0], self.itemData[assetId][19], self.itemData[assetId][5]
                        theirOffer.append(self.importLimited(item['assetId'], int(itemRap), int(itemValue), itemName, itemProjection, itemPrice))
                        theirValue += int(itemValue)
                        theirRap += int(itemRap)

                    self.putLimitedsInTradeScreen(myOffer, theirOffer, myValue, theirValue, myRap, theirRap, r['offers'][1]['user'])
                    self.ignore_trades.append(tradeId)
                    break

                else:
                    time.sleep(60)
            except Exception as err:
                print(err)
                pass

    def importLimited(self, id, rap, value, name, projected, price):
        im = Image.open('limiteds/%s.png' % id).convert("RGBA")
        warning = Image.open('images/warning.png').convert("RGBA")
        temp = rolimonsICO.copy()
        limited = background.copy()
        roblox = robloxICO.copy()

        warning.thumbnail((15, 15))
        im.thumbnail((126, 126))
        roblox.thumbnail((15, 15))
        limited.paste(im, (17, 22), im)
        if projected == '1': limited.paste(warning, (109, 14), warning)

        draw = ImageDraw.Draw(limited)
        limited.paste(temp, (12, 228), temp)
        limited.paste(roblox, (12, 210), roblox)
        draw.text((30, 190), humanize.intcomma(rap), (255,255,255), font=font)
        draw.text((30, 230), humanize.intcomma(value), (255,255,255), font=font)
        draw.text((30, 210), humanize.intcomma(price), (255,255,255), font=font)

        for i in range(len(textwrap.wrap(name, 12))):
            if i == 1: break
            draw.text((12, 144 + (i*20)), textwrap.wrap(name, 12)[i], (255,255,255), font=font)

        return limited

    def putLimitedsInTradeScreen(self, sent, received, myValue, theirValue, myRap, theirRap, ownerInfo):
        trade = tradeBackground.copy()

        for i in range(len(sent)):
            trade.paste(sent[i], (15 + (140*i), 40))

        for i in range(len(received)):
            trade.paste(received[i], (15 + (140*i), 425))

        draw = ImageDraw.Draw(trade)
        draw.text((470, 327.5), humanize.intcomma(myRap), (255,255,255), font=fontBig)
        draw.text((470, 349.5), humanize.intcomma(myValue), (255,255,255), font=fontBig)
        draw.text((470, 708), humanize.intcomma(theirRap), (255,255,255), font=fontBig)
        draw.text((470, 730), humanize.intcomma(theirValue), (255,255,255), font=fontBig)

        draw.text((10, 745), f'USERNAME: {ownerInfo["name"]} ({ownerInfo["displayName"]})', (255,255,255), font=fontSmall)

        rgb_im = trade.convert('RGB')
        rgb_im.save(f'{self.username}.jpg')
        with open(f'{self.username}.jpg', "rb") as f:
            self.webhook.add_file(file=f.read(), filename='inbound.jpg')
            self.webhook.content = f'<@{config["discordId"]}>'
            self.webhook.execute()

    def looping(self):
        if not config['sendOldInbounds']: self.getOldInbounds()
        while True:
            self.getInbounds()
            time.sleep(60)


Player()
