import discord
from discord.ext import commands
import matplotlib
import matplotlib.pyplot as plt
import sqlite3
from itertools import cycle
import os
import io

from functions.common import custom_cooldown


async def generate_maps(flag):

    lons1 = []
    lats1 = []
    lons2 = []
    lats2 = []
    colors1 = []
    colors2 = []
    img = ''
    map_extent = ()
    DB_LOCATION = str(os.getenv("DB_LOCATION"))
    DB_FILE = str(os.getenv("DB_FILE"))
    MAP_LOCATION = str(os.getenv("MAP_LOCATION"))
    EL_MAP_FILE = str(os.getenv("EL_MAP_FILE"))
    SIPTAH_MAP_FILE = str(os.getenv("SIPTAH_MAP_FILE"))

    print(f'loaded vars')

    filter_string1 = f'foundation'
    filter_string2 = f'pillar'
    filter_strings = ['foundation', 'pillar']
    # filter_strings = []
    # filter_strings = ['BasePlayerChar_C']
    once = False
    where_clause = ''
    flag_int = 0

    try:
        flag_int = int(flag)
        flag = 'clan'
    except ValueError:
        print(f'The flag was not an integer')
        pass

    if flag == 'buildings':
        if len(filter_strings) > 1:
            for strings in filter_strings:
                if not once:
                    where_clause += f'where class like \'%{strings}%\' '
                    once = True
                else:
                    where_clause += f'or class like \'%{strings}%\' '
        elif len(filter_strings) == 0:
            pass
        else:
            where_clause = f'where class like \'%{filter_strings[0]}%\' '

        print(where_clause)
    elif flag == f'clan':
        where_clause = f'where buildings.owner_id = {flag_int} and class not like \'%BasePlayerChar_C%\' '
    elif flag == f'all':
        where_clause = ''
    matplotlib.use('Agg')

    print(os.getcwd())
    el_path = os.path.abspath(f'{MAP_LOCATION}/{EL_MAP_FILE}')
    siptah_path = os.path.abspath(f'{MAP_LOCATION}/{SIPTAH_MAP_FILE}')

    img1 = plt.imread(el_path)
    img2 = plt.imread(siptah_path)

    with plt.style.context('dark_background'):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4), layout="constrained")

    map_extent1 = (-340000, 475000, -370000, 445000)
    ax1.set_xlim(-340000, 475000)
    ax1.set_ylim(-370000, 445000)
    ax1.tick_params(axis='x', labelsize=5)
    ax1.tick_params(axis='y', labelsize=5)
    ax1.get_xaxis().set_visible(False)
    ax1.get_yaxis().set_visible(False)

    # map_extent2 = (1125000, 2000000, -500000, 400000)
    # ax2.set_xlim(1125000, 2010000)
    # ax2.set_ylim(-500000, 400000)
    map_extent2 = (1110000, 2012500, -500000, 400000)
    ax2.set_xlim(1110000, 2012500)
    ax2.set_ylim(-500000, 400000)
    ax2.tick_params(axis='x', labelsize=5)
    ax2.tick_params(axis='y', labelsize=5)
    ax2.get_xaxis().set_visible(False)
    ax2.get_yaxis().set_visible(False)

    # print(f'before imshow')

    ax1.imshow(img1, extent=map_extent1, aspect='equal', interpolation='nearest')
    ax2.imshow(img2, extent=map_extent2, aspect='equal', interpolation='nearest')

    # print(f'after imshow')

    db_string = f'{DB_LOCATION}' #/{DB_FILE}'
    # print(f'{db_string}')
    filepath = os.path.abspath(db_string)

    # print(os.path.exists(f'{filepath}'))
    final_path = f'{filepath}/{DB_FILE}'
    # print(final_path)
    # print(os.path.exists(f'{final_path}'))
    # print(os.system(f'ls -lat {filepath}'))
    # print(os.system(f'id'))

    connection = sqlite3.connect(f'{final_path}')

    cursor = connection.cursor()
    cursor.execute(f'SELECT x, y, buildings.owner_id FROM actor_position '
                   f'left join buildings on actor_position.id = buildings.object_id '
                   f'{where_clause}'
                   f'order by buildings.owner_id asc, x asc, y desc')
    rows = cursor.fetchall()
    connection.close()

    # print(f'db closed')

    colors = cycle(['blue', 'red', 'yellow', 'orange', 'green', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan'])
    saved_owner = 0

    color = colors
    saved_color = color

    for row in rows:

        if float(row[0]) > 700000:
            lons2.append(float(row[0]))
            lats2.append(-float(row[1]))
            next_owner = row[2]
            if saved_owner != next_owner:
                color = next(colors)
                saved_color = color
                colors2.append(color)
                saved_owner = row[2]
            else:
                color = saved_color
                colors2.append(color)
                saved_owner = row[2]
        else:
            lons1.append(float(row[0]))
            lats1.append(-float(row[1]))
            next_owner = row[2]
            if saved_owner != next_owner:
                color = next(colors)
                saved_color = color
                colors1.append(color)
                saved_owner = row[2]
            else:
                color = saved_color
                colors1.append(color)
                saved_owner = row[2]

    # print(f'before scatter')

    ax1.scatter(lons1, lats1, linewidth=0.2, color=colors1, edgecolors='black', marker='o', s=3)
    ax2.scatter(lons2, lats2, linewidth=0.2, color=colors2, edgecolors='black', marker='o', s=3)
    # ax1.scatter(lons1, lats1, linewidth=0.2, color=colors1, edgecolors=colors1, marker='o', s=3)
    # ax2.scatter(lons2, lats2, linewidth=0.2, color=colors2, edgecolors=colors2, marker='o', s=3)

    # ax1.set_cmap('plasma')
    # ax2.set_cmap('plasma')

    # plt.savefig(f'{filepath}/high_res_output.png', dpi=1440, bbox_inches='tight')
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=1440, bbox_inches='tight')
    buffer.seek(0)
    file = discord.File(buffer, filename='high_res_output.png')
    # file = discord.File(f'{filepath}/high_res_output.png')
    # print(f'saved file')

    plt.close()

    return file
    # plt.show()


class BuildMap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='buildinfo', aliases=['buildmap'])
    @commands.has_any_role('Admin', 'Moderator')
    async def buildinfo(self, ctx, flag: str = 'buildings'):
        """
        Generates a build map

        Parameters
        ----------
        ctx
        flag
            Filter to use for build pieces

        Returns
        -------

        """
        image_file = await generate_maps(flag)
        await ctx.reply(f'Build map has been generated', file=image_file)
        return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog((BuildMap(bot)))
