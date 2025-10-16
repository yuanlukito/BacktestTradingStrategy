import streamlit as st
import vectorbt as vbt
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import copy
import plotly.graph_objs as go

st.title('💵 Trading Strategy Backtester')
st.write('Aplikasi ini menyediakan platform untuk menguji strategi trading pada berbagai aset seperti saham, cryptocurrency, dan forex menggunakan data historis.')

st.divider()

st.header('1. Pemilihan Trading Strategy')
st.write('Pilih strategi trading yang ingin Anda uji. Anda dapat mengubah parameter-parameter strategi sesuai kebutuhan.')

pilihan_strategy = st.selectbox(
    'Pilih Strategi',
    ('Moving Average Crossover', 'Mean Reversion', 'RSI Strategy')
)

st.session_state['strategy'] = pilihan_strategy

if pilihan_strategy == 'Moving Average Crossover':
    st.subheader('Moving Average Crossover')
    st.write('Strategi ini melibatkan dua moving averages: satu dengan periode pendek dan satu dengan periode panjang. Sinyal beli dihasilkan ketika moving average jangka pendek melintasi di atas moving average jangka panjang, dan sinyal jual dihasilkan ketika moving average jangka pendek melintasi di bawah moving average jangka panjang.')
    
    pilihan_ma = st.radio(
        'Pilih Jenis Moving Average', 
        ('Simple Moving Average (SMA)', 'Exponential Moving Average (EMA)')
    )

    st.session_state['ma_type'] = pilihan_ma

    col1, col2 = st.columns(2)
    with col1:
        short_window = st.number_input('Periode Moving Average Pendek', min_value=1, max_value=100, value=20)
    with col2:
        long_window = st.number_input('Periode Moving Average Panjang', min_value=1, max_value=200, value=50)

    st.write(f'Anda telah memilih {pilihan_ma} dengan periode pendek {short_window} dan periode panjang {long_window}.')

    st.session_state['parameters'] = {
        'short_window': short_window,
        'long_window': long_window
    }

st.divider()

st.header('2. Pemilihan Aset (Saham, Crypto, Forex)')
st.write('Pilih aset yang ingin Anda perdagangkan. Anda dapat memilih dari saham, cryptocurrency, atau pasangan mata uang forex.  Gunakan simbol ticker sesuai dengan platform Yahoo Finance.')
ticker = st.text_input('Masukkan Ticker Aset (misal: TLKM.JK untuk saham Telkom, AAPL untuk Apple, BTC-USD untuk Bitcoin, EURUSD=X untuk Euro/USD)', 'AAPL')
if st.button('Tambahkan ke Daftar Aset'):
    if 'asset_list' not in st.session_state:
        st.session_state['asset_list']['ticker'] = dict()
    if 'ticker' not in st.session_state['asset_list']:
        st.session_state['asset_list']['ticker'] = []
    if ticker not in st.session_state['asset_list']['ticker']:
        st.session_state['asset_list']['ticker'].append(ticker)
    else:
        st.warning('Aset sudah ada dalam daftar.')

if 'asset_list' not in st.session_state:
    st.session_state['asset_list'] = {'ticker': []}
asset_df = pd.DataFrame(st.session_state['asset_list'])
st.write(asset_df)

if st.button('Hapus Semua Aset'):
    st.session_state['asset_list'] = {'ticker': []}
    st.rerun() 

st.header('3. Pemilihan Periode Backtest')
st.write('Tentukan periode waktu untuk backtest. Anda dapat memilih tanggal mulai dan tanggal akhir.')

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input('Tanggal Mulai', pd.to_datetime('2021-01-01'))
with col2:
    end_date = st.date_input('Tanggal Akhir', pd.to_datetime('2024-12-31'))
if start_date >= end_date:
    st.error('Tanggal mulai harus sebelum tanggal akhir.')
else: 
    st.session_state['start_date'] = start_date
    st.session_state['end_date'] = end_date
    if st.button('Ambil Data Historis'):
        st.subheader('Data Historis Aset')
        if 'asset_list' in st.session_state and st.session_state['asset_list']['ticker']:
            all_data = {}
            for ticker in st.session_state['asset_list']['ticker']:
                data = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False, auto_adjust=False)
                if not data.empty:
                    all_data[ticker] = data
                    st.write(f'Data untuk {ticker}:')
                    st.line_chart(data['Close'])
                else:
                    st.warning(f'Tidak ada data untuk ticker: {ticker}')
            st.session_state['all_data'] = all_data


st.header('4. Hasil Backtest')
st.write('Hasil backtest mencakup metrik kinerja seperti total return, drawdown, dan rasio Sharpe.')

st.subheader('Parameter Backtest')
col1, col2 = st.columns(2)
with col1:
    initial_capital = st.number_input('Modal Awal:', min_value=1000, value=10000, step=1000)
with col2:
    fee = st.number_input('Biaya Perdagangan (%):', min_value=0.0, value=0.5, step=0.01)
st.session_state['backtest_params'] = {
    'initial_capital': initial_capital,
    'fee': fee / 100
}

if st.button('Jalankan Backtest'):
    if 'all_data' in st.session_state and st.session_state['all_data']:
        all_results = {}
        for ticker, data in st.session_state['all_data'].items():
            df = copy.deepcopy(data)
            if st.session_state['strategy'] == 'Moving Average Crossover':
                if st.session_state['ma_type'] == 'Simple Moving Average (SMA)':
                    df['SMA_Short'] = ta.sma(df['Close'], length=st.session_state['parameters']['short_window'])
                    df['SMA_Long'] = ta.sma(df['Close'], length=st.session_state['parameters']['long_window'])
                else:
                    df['EMA_Short'] = ta.ema(df['Close'], length=st.session_state['parameters']['short_window'])
                    df['EMA_Long'] = ta.ema(df['Close'], length=st.session_state['parameters']['long_window'])

                if st.session_state['ma_type'] == 'Simple Moving Average (SMA)':
                    entries = df['SMA_Short'] > df['SMA_Long']
                    exits = df['SMA_Short'] < df['SMA_Long']
                else:
                    entries = df['EMA_Short'] > df['EMA_Long']
                    exits = df['EMA_Short'] < df['EMA_Long']

                pf = vbt.Portfolio.from_signals(
                    close=df['Close'],
                    entries=entries,
                    exits=exits,
                    init_cash=st.session_state['backtest_params']['initial_capital'],
                    fees=st.session_state['backtest_params']['fee'],
                    freq='1D'
                )
                all_results[ticker] = pf

        st.subheader('Metrik Kinerja')
        stats_list = []
        for ticker, pf in all_results.items():
            st.write(f'### Hasil Backtest untuk {ticker}')
            stats = pf.stats()
            st.write(stats)
            stats_list.append(stats)

            st.subheader(f'Equity Curve untuk {ticker}')
            # PLOT
            equity_data = pf.value()
            drawdown_data = pf.drawdown()*100
            # Plotting the equity curve with Plotly
            equity_trace = go.Scatter(x=equity_data.index, y=equity_data, mode='lines', name='Equity Curve')
            equity_layout = go.Layout(title='Equity Curve', xaxis_title='Date', yaxis_title='Equity')
            equity_fig = go.Figure(data=[equity_trace], layout=equity_layout)
            st.plotly_chart(equity_fig)

            st.subheader(f'Drawdown untuk {ticker}')
            drawdown_trace = go.Scatter(
                x=drawdown_data.index,
                y=drawdown_data,
                mode='lines',
                name='Drawdown Curve',
                fill='tozeroy',
                line=dict(color='brown')
            )
            drawdown_layout = go.Layout(
                title='Drawdown Curve',
                xaxis_title='Date',
                yaxis_title='Drawdown %',
                template='plotly_white'
            )
            drawdown_fig = go.Figure(data=[drawdown_trace], layout=drawdown_layout)
            st.plotly_chart(drawdown_fig)

            st.subheader(f"Chart Portfolio dan Equity {ticker}")
            st.plotly_chart(pf.plot())
        
        if stats_list:
            stats_df = pd.DataFrame(stats_list, index=all_results.keys()).T
            st.write('### Perbandingan Metrik Kinerja Antar Aset')
            st.dataframe(stats_df)
    else:
        st.warning('Tidak ada data aset untuk melakukan backtest. Silakan tambahkan aset dan ambil data historis terlebih dahulu.')