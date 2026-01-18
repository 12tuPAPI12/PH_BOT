import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta

TOKEN = 'My Super Secret Token'
BASE_URLS = [
    'https://www.pornhub.com/video?o=tr&t=all',
    'https://www.pornhub.com/video?o=tr',
    'https://www.pornhub.com/video?o=mv&t=all',
]
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

class PornhubScraper:
    def __init__(self):
        self.cache = []
        self.last_scrape_time = None
        self.cache_duration = timedelta(hours=1)
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.session.cookies.set('accessAgeDisclaimerPH', '1', domain='.pornhub.com')
        self.session.cookies.set('age_verified', '1', domain='.pornhub.com')

    def _is_video_link(self, href):
        return 'view_video.php' in href or '/video/' in href

    def _extract_videos(self, soup, limit=5):
        selectors = [
            'a.videoPreviewBg',
            'a.linkVideoThumb',
            '.phimage a',
            '.title a',
            'a.title',
        ]
        anchors = soup.select(','.join(selectors))
        videos = []
        seen = set()

        for link_tag in anchors:
            if len(videos) >= limit:
                break

            href = link_tag.get('href')
            if not href or not self._is_video_link(href):
                continue

            if not href.startswith('http'):
                href = 'https://www.pornhub.com' + href

            if href in seen:
                continue

            title = link_tag.get('title') or link_tag.get('data-title')
            if not title:
                img_tag = link_tag.find('img')
                title = img_tag.get('alt') if img_tag else None
            if not title:
                title = link_tag.get_text(strip=True)

            if not title:
                continue

            seen.add(href)
            videos.append({'title': title, 'url': href})

        return videos

    def scrape_videos(self):
        if self.last_scrape_time and datetime.now() - self.last_scrape_time < self.cache_duration:
            return self.cache

        for url in BASE_URLS:
            try:
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching URL ({url}): {e}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            videos = self._extract_videos(soup, limit=5)
            if videos:
                self.cache = videos
                self.last_scrape_time = datetime.now()
                return videos

        return []

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
scraper = PornhubScraper()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command(name='hotxd', help='Shows the top 5 global PH videos')
async def ph_hot(ctx):
    async with ctx.typing():
        videos = await asyncio.to_thread(scraper.scrape_videos)

        if not videos:
            await ctx.send("No videos could be retrieved at this time. Please try again later.")
            return

        embed = discord.Embed(
            title="Top 5 Global PH Videos - PH",
            description="The hottest videos right now.",
            color=0xff9900,
            timestamp=datetime.now()
        )

        for i, video in enumerate(videos, 1):
            embed.add_field(
                name=f"{i}. {video['title']}",
                value=f"[Watch Video]({video['url']})",
                inline=False
            )

        embed.set_footer(text="Requested by " + ctx.author.display_name)

    await ctx.send(embed=embed)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: Please edit the file and put your Discord token in the TOKEN variable.")
        print("Testing scraper locally...")
        results = scraper.scrape_videos()
        for idx, vid in enumerate(results, 1):
            try:
                print(f"{idx}. {vid['title']} - {vid['url']}")
            except UnicodeEncodeError:
                print(f"{idx}. {vid['title'].encode('utf-8', 'ignore').decode('utf-8')} - {vid['url']}")
    else:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("ERROR: Invalid Discord token.")
