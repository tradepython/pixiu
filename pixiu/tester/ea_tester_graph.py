# import matplotlib.pyplot as plt
# from mplfinance.original_flavor import candlestick_ohlc
# import matplotlib.dates as mpl_dates
import dash
from dash.dependencies import Output, Input, State
from dash import dcc, html
from dash.exceptions import PreventUpdate
import plotly
from plotly.subplots import make_subplots
import random
import plotly.graph_objs as go
from collections import deque
from multiprocessing import (Pool, Process, Manager, Queue, Value)
from flask import request
import sys
from urllib.request import Request, urlopen
import traceback
import threading
import time
import os
import json
import pandas as pd, numpy as np
import random

# dados = np.array([[1509608700000,0.00002246,0.00002246,0.00002246,0.00002246,100.00000000,1509609599999],
# [1509609600000,0.00002800,0.00002802,0.00002800,0.00002800,6832.00000000,1509610499999],
# [1509610500000,0.00002700,0.00002700,0.00002501,0.00002501,3936.00000000,1509611399999],
# [1509611400000,0.00002588,0.00002678,0.00002588,0.00002614,7125.00000000,1509612299999],
# [1509612300000,0.00002615,0.00002621,0.00002614,0.00002617,19318.00000000,1509613199999],
# [1509613200000,0.00002627,0.00002643,0.00002625,0.00002627,109218.00000000,1509614099999],
# [1509614100000,0.00002627,0.00002642,0.00002603,0.00002639,134825.00000000,1509614999999],
# [1509615000000,0.00002639,0.00002655,0.00002616,0.00002618,74432.00000000,1509615899999]
# ])
#
# columns = ['open_time', 'open', 'high', 'low','close', 'volume', 'close_time']
#
# df = pd.DataFrame(data=dados, columns=columns)
#
# last_id = 0

# external_stylesheets = ["https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/css/materialize.min.css"]
# external_scripts = ['https://cdnjs.cloudflare.com/ajax/libs/materialize/0.100.2/js/materialize.min.js']
# app = dash.Dash(__name__,external_scripts=external_scripts,
#                 external_stylesheets=external_stylesheets)

app = dash.Dash(__name__)

g_data_queue = deque(maxlen=100)

# X = deque(maxlen=20)
# X.append(1)
#
# Y = deque(maxlen=20)
# Y.append(1)

# price_info = np.array([],
#                  dtype=[('t', float), ('o', float), ('h', float), ('c', float),
#                         ('l', float), ('v', float) ])
#

# g_fig = make_subplots(rows=1, cols=1)
# # plot = fig.get_subplot(row=1, col=1)
# g_fig.add_trace(go.Candlestick(
#     x=[],
#     open=[],
#     high=[],
#     low=[],
#     close=[]),
#     row=1,
#     col=1,
# )

g_graph_group = {}
g_last_relayout = None
g_group_options = []
g_group_selected = None
g_group_items_selected = None

def set_subplot(fig, group_member, last_relayout, row, col):
    name = group_member['name']
    symbol = group_member['symbol']
    graph_info = group_member['graph_info']
    range = None
    if last_relayout:
        range = last_relayout.get('xaxis.range', None)
        if range is None:
            range = [last_relayout.get('xaxis.range[0]', None), last_relayout.get('xaxis.range[1]', None)]

    #
    new_price_count = len(graph_info['price'])
    price_count = graph_info['update'].get('price_count', 0)
    price_info = graph_info.get('price_info', None)
    if price_info is None or new_price_count > price_count:
        price_info = pd.DataFrame(graph_info['price'][0:new_price_count])
        price_info.columns = ['t', 'o', 'h', 'c', 'l', 'v', 'equity', 'balance', 'margin']
        price_info['t'] = pd.to_datetime(price_info['t'], unit='s')
        price_info.set_index('t', inplace=True)
        price_count = new_price_count
        #
        candlestick = go.Candlestick(
            x=price_info.index,
            open=price_info['o'],
            high=price_info['h'],
            low=price_info['l'],
            close=price_info['c'],
            name='price'
        )
        equity_line = go.Scatter(
            x=price_info.index,
            y=price_info['equity'],
            name='equity'
        )
        balance_line = go.Scatter(
            x=price_info.index,
            y=price_info['balance'],
            name='balance'
        )
        margin_line = go.Scatter(
            x=price_info.index,
            y=price_info['margin'],
            name='margin'
        )
        graph_info['price_info'] = price_info
        graph_info['price_candlestick'] = candlestick
        graph_info['equity_line'] = equity_line
        graph_info['balance_line'] = balance_line
        graph_info['margin_line'] = margin_line
        #
        count = int(price_info.index.size * 0.1)
        sindex = price_info.index.size - count
        if sindex < 0:
            sindex = 0
        # new_price_count - price_count
        range = [price_info.index[sindex], price_info.index[-1]]
    # else:
    #     raise PreventUpdate

    #
    new_order_count = len(graph_info['order'])
    order_count = graph_info['update'].get('order_count', 0)
    order_info = graph_info.get('order_info', None)
    if order_info is None or new_order_count > order_count:
        order_info = pd.DataFrame(graph_info['order'])
        order_info.columns = ['t', 'price', 'marker_pos', 'h', 'l', 'type', 'symbol', 'line_color', 'color', 'text']
        order_info['t'] = pd.to_datetime(order_info['t'], unit='s')
        order_info.set_index('t', inplace=True)
        order_count = new_order_count
        order_markers = go.Scatter(
            x=order_info.index,
            y=order_info['marker_pos'],
            text=order_info['text'],
            marker=dict(symbol=order_info['symbol'],
                        line_color=order_info['line_color'],
                        color=order_info['color'], ),
            # marker_symbol=order_info['symbol'],
            # marker_line_color=order_info['line_color'],
            # marker_color=order_info['color'],
            marker_line_width=1,
            marker_size=8,
            mode='markers',
            name='orders'
        )
        graph_info['order_info'] = order_info
        graph_info['order_markers'] = order_markers


    fig.add_trace(graph_info['price_candlestick'],
        row=row,
        col=col,
    )
    fig.add_trace(graph_info['equity_line'],
        secondary_y=True,
        row=row,
        col=col,
    )
    fig.add_trace(graph_info['balance_line'],
        secondary_y=True,
        row=row,
        col=col,
    )
    fig.add_trace(graph_info['margin_line'],
        secondary_y=True,
        row=row,
        col=col,
    )
    fig.add_trace(graph_info['order_markers'],
        # secondary_y=True,
        row=row,
        col=col,
    )
    fig.add_annotation(xref="x domain", yref="y domain", x=0.5, y=1.2, showarrow=False,
                       text=f"{name} @{symbol}", row=row, col=col)
    # print(f"range={range}")
    # fig.update_layout(
    #     title_text=f"{name} @{symbol}",
    #     title_font_size=30, height=1600,
    #     xaxis=dict(
    #         rangeslider=dict(
    #             visible=False,
    #             # range=[order_info.index[0], order_info.index[3]]
    #         ),
    #         range=range,#['2022-06-13 23:17:00', '2022-06-14 23:17:00']
    #         # type="date"
    #     )
    # )

    graph_info['update']['price_count'] = price_count
    graph_info['update']['order_count'] = order_count
    ret = dict(xaxis=dict(
            rangeslider=dict(
                visible=True,
            ),
            range=range,#['2022-06-13 23:17:00', '2022-06-14 23:17:00']
            # type="date"
        ))
    return ret

#
# def set_subplot(fig, group_member, last_relayout, row, col):
#     # global g_graph_group
#     # ###SUBPLOT AND Candlestick CHART
#     # group = 'default'
#     # members_count = len(g_graph_group[group])
#     #
#     # g_fig = make_subplots(rows=members_count, cols=1, specs=[[{"secondary_y": True}]])
#     # row = 1
#     # for name in g_graph_group[group]:
#     #     member = g_graph_group[group][name]
#         name = group_member['name']
#         symbol = group_member['symbol']
#         graph_info = group_member['graph_info']
#         range = None
#         if last_relayout:
#             range = last_relayout.get('xaxis.range', None)
#             if range is None:
#                 range = [last_relayout.get('xaxis.range[0]', None), last_relayout.get('xaxis.range[1]', None)]
#
#         #
#         new_price_count = len(graph_info['price'])
#         price_count = graph_info['update'].get('price_count', 0)
#         price_info = graph_info.get('price_info', None)
#         if price_info is None or new_price_count > price_count:
#             price_info = pd.DataFrame(graph_info['price'][0:new_price_count])
#             price_info.columns = ['t', 'o', 'h', 'c', 'l', 'v', 'equity', 'balance', 'margin']
#             price_info['t'] = pd.to_datetime(price_info['t'], unit='s')
#             price_info.set_index('t', inplace=True)
#             price_count = new_price_count
#             #
#             candlestick = go.Candlestick(
#                 x=price_info.index,
#                 open=price_info['o'],
#                 high=price_info['h'],
#                 low=price_info['l'],
#                 close=price_info['c'],
#                 name='price'
#             )
#             equity_line = go.Scatter(
#                 x=price_info.index,
#                 y=price_info['equity'],
#                 name='equity'
#             )
#             balance_line = go.Scatter(
#                 x=price_info.index,
#                 y=price_info['balance'],
#                 name='balance'
#             )
#             margin_line = go.Scatter(
#                 x=price_info.index,
#                 y=price_info['margin'],
#                 name='margin'
#             )
#             graph_info['price_info'] = price_info
#             graph_info['price_candlestick'] = candlestick
#             graph_info['equity_line'] = equity_line
#             graph_info['balance_line'] = balance_line
#             graph_info['margin_line'] = margin_line
#             #
#             count = int(price_info.index.size * 0.1)
#             sindex = price_info.index.size - count
#             if sindex < 0:
#                 sindex = 0
#             # new_price_count - price_count
#             range = [price_info.index[sindex], price_info.index[-1]]
#         else:
#             raise PreventUpdate
#
#         #
#         new_order_count = len(graph_info['order'])
#         order_count = graph_info['update'].get('order_count', 0)
#         order_info = graph_info.get('order_info', None)
#         if order_info is None or new_order_count > order_count:
#             order_info = pd.DataFrame(graph_info['order'])
#             order_info.columns = ['t', 'price', 'marker_pos', 'h', 'l', 'type', 'symbol', 'line_color', 'color', 'text']
#             order_info['t'] = pd.to_datetime(order_info['t'], unit='s')
#             order_info.set_index('t', inplace=True)
#             order_count = new_order_count
#             order_markers = go.Scatter(
#                 x=order_info.index,
#                 y=order_info['marker_pos'],
#                 text=order_info['text'],
#                 marker=dict(symbol=order_info['symbol'],
#                             line_color=order_info['line_color'],
#                             color=order_info['color'], ),
#                 # marker_symbol=order_info['symbol'],
#                 # marker_line_color=order_info['line_color'],
#                 # marker_color=order_info['color'],
#                 marker_line_width=1,
#                 marker_size=8,
#                 mode='markers',
#                 name='orders'
#             )
#             graph_info['order_info'] = order_info
#             graph_info['order_markers'] = order_markers
#
#
#         fig.add_trace(graph_info['price_candlestick'],
#             row=row,
#             col=col,
#         )
#         fig.add_trace(graph_info['equity_line'],
#             secondary_y=True,
#             row=row,
#             col=col,
#         )
#         fig.add_trace(graph_info['balance_line'],
#             secondary_y=True,
#             row=row,
#             col=col,
#         )
#         fig.add_trace(graph_info['margin_line'],
#             secondary_y=True,
#             row=row,
#             col=col,
#         )
#         fig.add_trace(graph_info['order_markers'],
#             # secondary_y=True,
#             row=row,
#             col=col,
#         )
#         print(f"range={range}")
#         fig.update_layout(
#             title_text=f"{name} @{symbol}",
#             title_font_size=30, height=1600,
#             xaxis=dict(
#                 rangeslider=dict(
#                     visible=False,
#                     # range=[order_info.index[0], order_info.index[3]]
#                 ),
#                 range=range,#['2022-06-13 23:17:00', '2022-06-14 23:17:00']
#                 # type="date"
#             )
#         )
#
#         graph_info['update']['price_count'] = price_count
#         graph_info['update']['order_count'] = order_count
#

# price_info = None
# graph_info = []
@app.callback(
    Output('live-graph', 'figure'),
    [Input('graph-update', 'n_intervals')]
)
def graph_update(n):
    global g_graph_group, g_group_selected, g_group_items_selected
    ###SUBPLOT AND Candlestick CHART
    if g_group_selected is None:
        print(f"graph_update: g_group_selected={g_group_selected}")
        raise PreventUpdate
    if g_group_selected not in g_graph_group:
        print(f"graph_update: g_graph_group={g_graph_group}")
        raise PreventUpdate
    if g_group_items_selected is None or len(g_group_items_selected) == 0:
        print(f"graph_update: g_group_items_selected={g_group_items_selected}")
        raise PreventUpdate
    group = g_group_selected
    members_count = len(g_group_items_selected)

    # g_fig = make_subplots(rows=members_count+1, cols=1, specs=[[{"secondary_y": True}], [{"secondary_y": True}]])
    specs = []
    for i in range(members_count):
        specs.append([{"secondary_y": True}])
    g_fig = make_subplots(rows=members_count, cols=1,
                          shared_xaxes=True,
                          specs=specs,
                          subplot_titles=("Plot 1", "Plot 2", "Plot 3", "Plot 4"))
    row = 1
    col = 1
    xaxis = []
    for name in g_graph_group[group]:
        if name not in g_group_items_selected:
            continue
        member = g_graph_group[group][name]
        # name = member['name']
        # symbol = member['symbol']
        # graph_info = member['graph_info']
        # range = None
        # if g_last_relayout:
        #     range = g_last_relayout.get('xaxis.range', None)
        #     if range is None:
        #         range = [g_last_relayout.get('xaxis.range[0]', None), g_last_relayout.get('xaxis.range[1]', None)]
        st = time.time()
        ret = set_subplot(g_fig, member, g_last_relayout, row, col)
        print(f"set_subplot: {row}, {col} ... {time.time() - st}")
        xaxis.append(ret['xaxis'])
        row += 1
    # print(f"range={range}")
    layout = dict(title_font_size=30, height=500*members_count,)
    i = 1
    for xa in xaxis:
        layout[f'xaxis{i}'] = xa
        i += 1
    g_fig.update_layout(
        layout
        # title_text=f"{name} @{symbol}",
        # title_font_size=30, height=500*members_count,
        # xaxis=xaxis
    )
        # set_subplot(g_fig, member, g_last_relayout, row+1, col)
        # print(f"range={range}")
        # g_fig.update_layout(
        #     title_text=f"{name} @{symbol}",
        #     title_font_size=30, height=800,
        #     xaxis=dict(
        #         rangeslider=dict(
        #             visible=True,
        #             # range=[order_info.index[0], order_info.index[3]]
        #         ),
        #         range=range,#['2022-06-13 23:17:00', '2022-06-14 23:17:00']
        #         # type="date"
        #     )
        # )
        # row += 1
    return g_fig

@app.callback(
    Output('live-graph', 'children'),
    Input('live-graph', 'relayoutData'))
def display_relayout_data(relayoutData):
    global g_last_relayout
    g_last_relayout = relayoutData
    print(f"relayoutData={relayoutData}")
    #relayoutData={'xaxis.range': ['2022-06-14 07:28:10.9357', '2022-06-15 10:47']}
    return json.dumps(relayoutData, indent=2)

@app.callback(
    Output("group-list", "options"),
    Input("group-list", "search_value")
)
def update_options(search_value):
    global g_group_options
    # if not search_value:
    #     raise PreventUpdate
    return [o for o in g_group_options]

@app.callback(
    Output('group-list', 'children'),
    Input('group-list', 'value')
)
def update_group_list_output(value):
    global g_group_selected
    g_group_selected = value
    print(f"g_group_selected={g_group_selected}")
    return f'You have selected {value}'

@app.callback(
    Output("group-items-list", "options"),
    Output("group-items-list", "value"),
    Input('group-list', 'value'),
    # State("group-items-list", "value")
)
def update_group_items_list_options(value):
    global g_graph_group, g_group_selected
    # if not search_value:
    #     raise PreventUpdate
    # Make sure that the set values are in the option list, else they will disappear
    # from the shown select list, but still part of the `value`.
    # group = g_group_selected
    group = value
    if group not in g_graph_group:
        raise PreventUpdate
    options = []
    for name in g_graph_group[group]:
        options.append(dict(label=name, value=name))
    values_selected = []
    # print(f"options={options}, g_graph_group={g_graph_group}")

    return options, values_selected

@app.callback(
    Output('group-items-list', 'children'),
    Input('group-items-list', 'value')
)
def update_group_items_list_output(value):
    global g_group_items_selected
    g_group_items_selected = value
    print(f"g_group_items_selected={g_group_items_selected}")
    return f'You have selected {value}'

#
# global_message_queue = Queue()

class EATesterGraphServer:
    def __init__(self, message_queue):
        self.running = Value('b', False)
        self.message_queue = message_queue

    def __process_queue_message__(self, message):
            global g_graph_group, g_group_selected
            try:
                data = json.loads(message)
                if data['cmd'] == 'update_data':
                    #name=self.test_name, symbol=self.symbol, group=self.symbol
                    name = data['name']
                    symbol = data['symbol']
                    group = data['group']
                    price = data['data']['price']
                    g_data_queue.append(price)
                    graph_id = 0
                    if group not in g_graph_group:
                        g_graph_group[group] = {}
                        g_group_options.append({"label": group, "value": group})
                        if g_group_selected is None:
                            g_group_selected = group
                    if name not in g_graph_group[group]:
                        g_graph_group[group][name] = dict(name=name, symbol=symbol, group=group,
                                                          graph_info=dict(price=[], order=[], update={}))
                        print(f"g_graph_group{group}={g_graph_group[group].keys()}")

                    graph_info = g_graph_group[group][name]['graph_info']
                    #
                    graph_info['price'].append(
                        [price['t'], price['o'], price['h'], price['c'], price['l'], price['v'],
                         price['equity'], price['balance'], price['margin']])
                    for o in price['orders']:
                        # info = f"#{o['uid']}, volume: {o['volume']}, price: {o['price']}, tp: {o.get('take_profit', '')}, sl: {o.get('stop_loss', '')}\n tags: {o.get('tags', '')}, "
                        info = f"#{o['uid']}, volume: {o['volume']}, price: {o['price']}, tp: {o.get('take_profit', '')}, sl: {o.get('stop_loss', '')}"
                        if o['type'] == 'BUY':
                            marker_pos = price['l'] - (price['h'] - price['l']) * 0.1
                            marker_line_color="#ffffff"
                            marker_color="blue"
                            symbol = 'arrow-up'
                            text = f"BUY: {info}"
                        elif o['type'] == 'SELL':
                            marker_pos = price['h'] + (price['h'] - price['l']) * 0.1
                            marker_line_color="#ffffff"
                            marker_color="blue"
                            symbol = 'arrow-down'
                            text = f"SELL: {info}"
                            # graph_info[graph_id]['order'].append([price['t'], o['price'], marker_pos, price['h'],
                            #                                       price['l'], 'sell',
                            #                                       'arrow-down', marker_line_color, marker_color,
                            #                                       text])
                        elif o['type'] == 'MODIFY':
                            marker_pos = price['h'] + (price['h'] - price['l']) * 0.1
                            marker_line_color="#ffffff"
                            marker_color="blue"
                            symbol = 'circle'
                            text = f"MODIFY: {info}"
                        elif o['type'] == 'CLOSE' or o['type'] == 'CLOSE_MULTI_ORDERS':
                            marker_pos = price['h'] + (price['h'] - price['l']) * 0.1
                            marker_line_color="#ffffff"
                            if o['profit'] > 0:
                                marker_color="green"
                            else:
                                marker_color="red"
                            symbol = 'square'
                            text = f"CLOSE: {info}, profit: {o['profit']}"
                        else:
                            continue
                        graph_info['order'].append([price['t'], o['price'], marker_pos, price['h'],
                                                              price['l'], o['type'],
                                                              symbol, marker_line_color, marker_color,
                                                              text])
            except Exception as ex:
                traceback.print_exc()


    def __message_thread__(self, message_queue):
        try:
            while self.running.value:
                if not message_queue.empty():
                    msg = message_queue.get_nowait()
                    # print(f"__message_thread__: {msg}")
                    if msg == 'stop':
                        break
                    self.__process_queue_message__(msg)
                else:
                    # print(f"__message_thread__: message_queue empty")
                    time.sleep(0.1)
        except:
            traceback.print_exc()
        print("Stop graph server ...")
        # sys.exit(0)
        os._exit(0)

    def __run_server__(self, message_queue):
        # app.layout = html.Div(
        #     [
        #         dcc.Graph(id='live-graph',
        #                   animate=True),
        #         dcc.Interval(
        #             id='graph-update',
        #             # interval=1000,
        #             interval=15000,
        #             n_intervals=0
        #         ),
        #     ]
        # )
        # app.layout = html.Div([
        #     # represents the browser address bar and doesn't render anything
        #     dcc.Location(id='url', refresh=False),
        #
        #     dcc.Graph(id='live-graph',
        #               animate=True),
        #     dcc.Interval(
        #         id='graph-update',
        #         interval=1000,
        #         n_intervals=0
        #     ),
        #
        #     # content will be rendered in this element
        #     html.Div(id='page-content', hidden=True)
        # ])
        app.layout = html.Div(
            html.Div(className='container-fluid', children=
            [
                html.Div([
                    "Group",
                    dcc.Dropdown(id="group-list")
                ]),
                html.Div([
                    "Group Items",
                    dcc.Dropdown(id="group-items-list", multi=True)
                ]),
                html.Div(className='row',
                         children=html.Div(dcc.Graph(id='live-graph',
                                                     animate=False,
                                                     # animate=True, animation_options=dict(redraw=True)
                                                     ),
                                           className='col s12 m12 l12')),
                dcc.Interval(
                    id='graph-update',
                    interval=5000,
                    n_intervals=0
                )
            ]),
        )

        self.running.value = True
        thread = threading.Thread(target=self.__message_thread__,
                                  args=(message_queue, ))
        thread.start()
        app.run_server(debug=False)

    def start(self):
        self.process = Process(target=self.__run_server__, args=(self.message_queue,))
        self.process.start()
        self.message_queue.put("start ...")
        # self.process.join()

    # def get_url_data(self, url, timeout=90):
    #     try:
    #         headers = {
    #             'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
    #         }
    #         req = Request(url, headers=headers)
    #         r = urlopen(req, timeout=timeout)
    #         content_type = r.headers.get('Content-Type', None)
    #         return r.code, content_type, r.read()
    #     except Exception as ex:
    #         traceback.print_exc()
    #     return None, None, None

    def join(self):
        self.process.join()

    def stop(self):
        pass
        # self.running.value = False

    def send_message(self, message):
        self.message_queue.put(message)