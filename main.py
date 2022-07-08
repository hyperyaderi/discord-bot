import os
import json
import sqlite3
import requests


from discord import FFmpegPCMAudio, Embed, Color
from discord.ext import commands 
from dotenv import load_dotenv
from discord.ext.commands import errors

load_dotenv()

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

TOKEN = os.getenv('DISCORD_TOKEN')

cursor.execute("""CREATE TABLE IF NOT EXISTS guilds(
    guild_id INT PRIMARY KEY,
    prefix STRING);
""")
conn.commit()

def is_guild_owner():
    def predicate(ctx):
        return ctx.guild is not None and ctx.guild.owner_id == ctx.author.id
    return commands.check(predicate)

def get_prefix(bot, message):
   guildid = message.guild.id
   cursor.execute("SELECT prefix FROM guilds WHERE guild_id = '%s'" % guildid)
   prefix = cursor.fetchone()[0]
   conn.commit()
   return prefix

bot = commands.Bot(command_prefix=get_prefix, help_command=None, case_insensitive=True)

@bot.event
async def on_ready():
    print('Music Bot Ready')

@bot.event
async def on_guild_join(guild): 
    cursor.execute("INSERT INTO guilds VALUES (?, ?)", (guild.id, '~'))
    conn.commit()

@bot.event
async def on_guild_remove(guild):
    cursor.execute("DELETE FROM guilds WHERE guild_id = '%s'" % guild.id)
    conn.commit()

@bot.command()
@commands.has_permissions(administrator=True)
async def changeprefix(ctx, prefix):
    guildid = ctx.guild.id
    cursor.execute(f"UPDATE guilds SET prefix= '{prefix}' WHERE guild_id = '{guildid}';")
    conn.commit()
    emb = Embed(title='Выполнено успешно!', description=f'Префикс сервера изменен на "** {prefix} **"', colour=Color.green(), timestamp=ctx.message.created_at)
    emb.set_footer(text=ctx.message.author)
    await ctx.send(embed=emb)

@bot.command(aliases=['c', 'h', 'help'])
async def commands(ctx):
    emb = Embed(title='Команды', description=f'play - начать воспроизведение\nstop - завершить\nchangeprefix - сменить префикс\nnowplaying - узнать какой трек сейчас играет\nlisteners - узнать кол-во слушателей', colour=Color.green(), timestamp=ctx.message.created_at)
    emb.set_footer(text=ctx.message.author)
    await ctx.send(embed=emb)

@bot.command(aliases=['p', 'pla'])
async def play(ctx):
    channel = ctx.author.voice.channel
    global player
    player = await channel.connect()
    player.play(FFmpegPCMAudio('http://localhost:1337/radio'))
    

@bot.command(aliases=['s', 'sto'])
async def stop(ctx):
    try:
        player.stop()
        await ctx.voice_client.disconnect()
    except NameError:
        emb = Embed(timestamp=ctx.message.created_at, title='Ошибка!!!', colour=Color.red(), description='Плеер не был запущен')
        emb.set_footer(text=ctx.message.author)
        await ctx.send(embed=emb)

@bot.command(aliases=['n', 'np', 'now'])
async def nowplaying(ctx):
    url = 'http://localhost:1337/status-json.xsl'
    resp = requests.get(url).text
    data = json.loads(resp)
    nowplaying = data['icestats']['source']['title']
    emb = Embed(timestamp=ctx.message.created_at, title='Сейчас играет', colour=Color.green(), description=nowplaying)
    emb.set_footer(text=ctx.message.author)
    await ctx.send(embed=emb)

@bot.command(aliases=['l', 'ls', 'list'])
async def listeners(ctx):
    url = 'http://localhost:1337/status-json.xsl'
    resp = requests.get(url).text
    data = json.loads(resp)
    listeners = data['icestats']['source']['listeners']
    listener_peak = data['icestats']['source']['listener_peak']
    emb = Embed(timestamp=ctx.message.created_at, title='Количество слушателей', colour=Color.green(), description=f'Сейчас: {listeners} чел.\nПик: {listener_peak} чел.')
    emb.set_footer(text=ctx.message.author)
    await ctx.send(embed=emb)

@changeprefix.error
async def prefix_error(ctx, exception):
    error = getattr(exception, "original", exception)
    if isinstance(error, errors.MissingRequiredArgument):
        emb = Embed(timestamp=ctx.message.created_at, title='Ошибка!!!', colour=Color.red(), description='Вы не указали префикс')
        emb.set_footer(text=ctx.message.author)
        await ctx.send(embed=emb)    

    if isinstance(error, errors.CheckFailure):
        emb = Embed(timestamp=ctx.message.created_at, title='Ошибка!!!', colour=Color.red(), description='Эту команду может использовать только владелец сервера')
        emb.set_footer(text=ctx.message.author)
        await ctx.send(embed=emb)    


@play.error
async def play_error(ctx, exception):
    error = getattr(exception, "original", exception)
    if isinstance(error, AttributeError):
        emb = Embed(timestamp=ctx.message.created_at, title='Ошибка!!!', colour=Color.red(), description='Вы должны находиться в голосовом канале')
        emb.set_footer(text=ctx.message.author)
        await ctx.send(embed=emb)    

@stop.error
async def stop_error(ctx, exception):
    error = getattr(exception, "original", exception)
    if isinstance(error, errors.CommandInvokeError):
        emb = Embed(timestamp=ctx.message.created_at, title='Ошибка!!!', colour=Color.red(), description='Вы должны находиться в голосовом канале')
        emb.set_footer(text=ctx.message.author)
        await ctx.send(embed=emb)    

bot.run(TOKEN)
