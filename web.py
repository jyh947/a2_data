# -*- coding: utf-8 -*-
from datetime import datetime
import argparse
import json

import requests
from flask import Flask, request, render_template
from requests.packages.urllib3.exceptions import InsecureRequestWarning

import config
import db
import utils
from names import POKEMON_NAMES

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import tweepy
import smtplib

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# Check whether config has all necessary attributes
REQUIRED_SETTINGS = (
    'GRID',
    'TRASH_IDS',
    'AREA_NAME',
    'REPORT_SINCE',
    'SCAN_RADIUS',
)
for setting_name in REQUIRED_SETTINGS:
    if not hasattr(config, setting_name):
        raise RuntimeError('Please set "{}" in config'.format(setting_name))



def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-H',
        '--host',
        help='Set web server listening host',
        default='127.0.0.1'
    )
    parser.add_argument(
        '-P',
        '--port',
        type=int,
        help='Set web server listening port',
        default=5000
    )
    parser.add_argument(
        '-d', '--debug', help='Debug Mode', action='store_true'
    )
    parser.set_defaults(DEBUG=True)
    return parser.parse_args()


app = Flask(__name__, template_folder='templates')


@app.route('/data')
def pokemon_data():
    return json.dumps(get_pokemarkers())


@app.route('/workers_data')
def workers_data():
    return json.dumps({
        'points': get_worker_markers(),
        'scan_radius': config.SCAN_RADIUS,
    })


@app.route('/')
def fullmap():
    map_center = utils.get_map_center()
    return render_template(
        'newmap.html',
        area_name=config.AREA_NAME,
        map_center=map_center,
    )

email_sent =[]
tweets_sent =[]

def get_pokemarkers():
    markers = []
    session = db.Session()
    pokemons = db.get_sightings(session)
    forts = db.get_forts(session)
    session.close()
    global email_sent
    global tweets_sent
    TWITTER_1 = 0
    TWITTER_2 = 0
    TWITTER_3 = 0
    TWITTER_4 = 0
    PASSWORD = 0
    for pokemon in pokemons:
        markers.append({
            'id': 'pokemon-{}'.format(pokemon.id),
            'type': 'pokemon',
            'trash': pokemon.pokemon_id in config.TRASH_IDS,
            'name': POKEMON_NAMES[pokemon.pokemon_id],
            'pokemon_id': pokemon.pokemon_id,
            'lat': pokemon.lat,
            'lon': pokemon.lon,
            'expires_at': pokemon.expire_timestamp,
        })
        name = POKEMON_NAMES[pokemon.pokemon_id]
        datestr = datetime.fromtimestamp(pokemon.expire_timestamp)
        dateoutput = datestr.strftime("%H:%M:%S")
        am_or_pm = " AM"
        temp_dateoutput = datestr.strftime("%H:%M:%S")
        time_now = datetime.now()
        diff_in_time = datestr - time_now
        diff_in_time_str_useless = str(diff_in_time).split(".")
        diff_in_time_str = diff_in_time_str_useless[0].split(":")
        diff_in_time_int = [int(i) for i in diff_in_time_str]
        mins = ''
        secs = ''
        if diff_in_time_int[1] is 1:
            mins = 'min '
        else:
            mins = 'mins '
        if diff_in_time_int[2] is 1:
            secs = 'sec '
        else:
            secs = 'secs '
        time_left_str = str(diff_in_time_int[1]) + mins + str(diff_in_time_int[2]) + secs
        mod_date = temp_dateoutput.split(":")
        mod_date_int = int(mod_date[0])
        if mod_date_int > 24:
            mod_date_int = mod_date_int - 24
            am_or_pm = " AM"
        elif mod_date_int == 24:
            mod_date_int = mod_date_int - 12
            am_or_pm = " AM"
        elif mod_date_int > 12:
            mod_date_int = mod_date_int - 12
            am_or_pm = " PM"
        elif mod_date_int == 12:
            am_or_pm = " PM"
        actual_dateoutput = str(mod_date_int) + ":" + mod_date[1] + ":" + mod_date[2] + am_or_pm
        new_lat = "%.8f" % float(pokemon.lat)
        new_lon = "%.8f" % float(pokemon.lon)

        missing = [2, 3, 5, 6, 24, 28, 38, 51, 53, 57, 62, 65, 67, 68, 76, 78, 82, 83, 85, 89, 101, 103, 107, 112, 113, 114, 115, 122, 130, 132, 139, 141, 144, 145, 146, 149, 150, 151]
        rare = [2, 3, 5, 6, 9, 24, 26, 28, 31, 34, 38, 40, 51, 53, 57, 59, 62, 65, 67, 68, 71, 76, 78, 82, 83, 84, 85, 87, 88, 89, 91, 94, 101, 103, 105, 106, 107, 110, 112, 113, 114, 115, 121, 122, 126, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 148, 149, 150, 151]
        rare_alert = ""
        if pokemon.pokemon_id in rare:
            rare_alert = "Rare Alert! "
        if pokemon.pokemon_id in missing and pokemon.expire_timestamp not in email_sent:
            msg = MIMEMultipart()
            msg['Subject'] = rare_alert + str(name) + " here 'til " + str(actual_dateoutput) + ' with ' + time_left_str + 'left'
            msg['From'] = "example@test.com"
            msg['To'] = "second@test.com"
            message_to_send = 'https://www.google.com/maps/dir/Current+Location/' + str(pokemon.lat) + ',' + str(pokemon.lon)
            part1 = MIMEText(message_to_send, 'plain')
            msg.attach(part1)
            print msg.as_string()
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.ehlo()
            server.starttls()
            server.login("example@test.com", PASSWORD)
            server.sendmail("example@test.com", "second@test.com", msg.as_string())
            email_sent.append(pokemon.expire_timestamp)
        tweet_pokemon = [2, 3, 5, 6, 8, 9, 24, 26, 27, 28, 31, 34, 36, 37, 38, 40, 45, 50, 51, 53, 55, 57, 59, 61, 62, 64, 65, 67, 68, 71, 73, 75, 76, 78, 80, 81, 82, 83, 84, 85, 87, 88, 89, 91, 94, 95, 99, 101, 103, 104, 105, 106, 107, 108, 110, 112, 113, 114, 115, 117, 121, 122, 123, 126, 127, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 148, 149, 150, 151]
        if pokemon.pokemon_id in tweet_pokemon and pokemon.expire_timestamp not in tweets_sent:
            message_to_send = rare_alert + str(name) + " here until " + str(actual_dateoutput) + ' with ' + time_left_str + 'left! https://www.google.com/maps/dir/Current+Location/' + str(new_lat) + ',' + str(new_lon)
            auth = tweepy.OAuthHandler(TWITTER_1, TWITTER_2)
            auth.set_access_token(TWITTER_3, TWITTER_3)
            api = tweepy.API(auth)
            try:
                api.update_status(status=message_to_send)
                print message_to_send
                print len(message_to_send)
            except:
                print message_to_send
            tweets_sent.append(pokemon.expire_timestamp)
    for fort in forts:
        if fort['guard_pokemon_id']:
            pokemon_name = POKEMON_NAMES[fort['guard_pokemon_id']]
        else:
            pokemon_name = 'Empty'
        markers.append({
            'id': 'fort-{}'.format(fort['fort_id']),
            'sighting_id': fort['id'],
            'type': 'fort',
            'prestige': fort['prestige'],
            'pokemon_id': fort['guard_pokemon_id'],
            'pokemon_name': pokemon_name,
            'team': fort['team'],
            'lat': fort['lat'],
            'lon': fort['lon'],
        })

    return markers


def get_worker_markers():
    markers = []
    points = utils.get_points_per_worker()
    # Worker start points
    for worker_no, worker_points in enumerate(points):
        coords = utils.get_start_coords(worker_no)
        markers.append({
            'lat': coords[0],
            'lon': coords[1],
            'type': 'worker',
            'worker_no': worker_no,
        })
        # Circles
        for i, point in enumerate(worker_points):
            markers.append({
                'lat': point[0],
                'lon': point[1],
                'type': 'worker_point',
                'worker_no': worker_no,
                'point_no': i,
            })
    return markers


@app.route('/report')
def report_main():
    session = db.Session()
    top_pokemon = db.get_top_pokemon(session)
    bottom_pokemon = db.get_top_pokemon(session, order='ASC')
    bottom_sightings = db.get_all_sightings(
        session, [r[0] for r in bottom_pokemon]
    )
    stage2_pokemon = db.get_stage2_pokemon(session)
    if stage2_pokemon:
        stage2_sightings = db.get_all_sightings(
            session, [r[0] for r in stage2_pokemon]
        )
    else:
        stage2_sightings = []
    js_data = {
        'charts_data': {
            'punchcard': db.get_punch_card(session),
            'top30': [(POKEMON_NAMES[r[0]], r[1]) for r in top_pokemon],
            'bottom30': [
                (POKEMON_NAMES[r[0]], r[1]) for r in bottom_pokemon
            ],
            'stage2': [
                (POKEMON_NAMES[r[0]], r[1]) for r in stage2_pokemon
            ],
        },
        'maps_data': {
            'bottom30': [sighting_to_marker(s) for s in bottom_sightings],
            'stage2': [sighting_to_marker(s) for s in stage2_sightings],
        },
        'map_center': utils.get_map_center(),
        'zoom': 13,
    }
    icons = {
        'top30': [(r[0], POKEMON_NAMES[r[0]]) for r in top_pokemon],
        'bottom30': [(r[0], POKEMON_NAMES[r[0]]) for r in bottom_pokemon],
        'stage2': [(r[0], POKEMON_NAMES[r[0]]) for r in stage2_pokemon],
        'nonexistent': [
            (r, POKEMON_NAMES[r])
            for r in db.get_nonexistent_pokemon(session)
        ]
    }
    session_stats = db.get_session_stats(session)
    session.close()

    area = utils.get_scan_area()

    return render_template(
        'report.html',
        current_date=datetime.now(),
        area_name=config.AREA_NAME,
        area_size=area,
        total_spawn_count=session_stats['count'],
        spawns_per_hour=session_stats['per_hour'],
        session_start=session_stats['start'],
        session_end=session_stats['end'],
        session_length_hours=int(session_stats['length_hours']),
        js_data=js_data,
        icons=icons,
        google_maps_key=config.GOOGLE_MAPS_KEY,
    )


@app.route('/report/<int:pokemon_id>')
def report_single(pokemon_id):
    session = db.Session()
    session_stats = db.get_session_stats(session)
    js_data = {
        'charts_data': {
            'hours': db.get_spawns_per_hour(session, pokemon_id),
        },
        'map_center': utils.get_map_center(),
        'zoom': 13,
    }
    session.close()
    return render_template(
        'report_single.html',
        current_date=datetime.now(),
        area_name=config.AREA_NAME,
        area_size=utils.get_scan_area(),
        pokemon_id=pokemon_id,
        pokemon_name=POKEMON_NAMES[pokemon_id],
        total_spawn_count=db.get_total_spawns_count(session, pokemon_id),
        session_start=session_stats['start'],
        session_end=session_stats['end'],
        session_length_hours=int(session_stats['length_hours']),
        google_maps_key=config.GOOGLE_MAPS_KEY,
        js_data=js_data,
    )


def sighting_to_marker(sighting):
    return {
        'icon': '/static/icons/{}.png'.format(sighting.pokemon_id),
        'lat': sighting.lat,
        'lon': sighting.lon,
    }


@app.route('/report/heatmap')
def report_heatmap():
    session = db.Session()
    pokemon_id = request.args.get('id')
    points = db.get_all_spawn_coords(session, pokemon_id=pokemon_id)
    session.close()
    return json.dumps(points)


if __name__ == '__main__':
    args = get_args()
    app.run(debug=True, threaded=True, host=args.host, port=args.port)
