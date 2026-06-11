import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
from mplsoccer import Pitch
import numpy as np

st.set_page_config(
    page_title="Football Analytics Dashboard",
    layout="wide"
)

# =====================================
# ŁADOWANIE DANYCH
# =====================================

@st.cache_data
def load_data(uploaded_file):
    content = uploaded_file.getvalue().decode("utf-8")
    events = json.loads(content)
    return pd.json_normalize(events)


uploaded_file = st.sidebar.file_uploader(
    "Wgraj plik events.json",
    type=["json"]
)

if uploaded_file is None:
    st.info("Wgraj plik JSON, aby rozpocząć analizę.")
    st.stop()

try:
    df = load_data(uploaded_file)

except Exception as e:
    st.error(f"Błąd ładowania danych: {e}")
    st.stop()

# =====================================
# WYBÓR ZAWODNIKA
# =====================================

players = sorted(
    df["player.name"].dropna().unique()
)

player = st.sidebar.selectbox(
    "Wybierz zawodnika",
    players
)

player_df = df[
    df["player.name"] == player
]

# =====================================
# KPI
# =====================================

passes = player_df[
    player_df["type.name"] == "Pass"
]

shots = player_df[
    player_df["type.name"] == "Shot"
]

successful_passes = passes[
    passes["pass.outcome.name"].isna()
]

xg = shots["shot.statsbomb_xg"].sum()

# =====================================
# xA
# =====================================

xa = 0

all_shots = df[
    df["type.name"] == "Shot"
]

for _, shot in all_shots.iterrows():

    try:
        assister = shot["pass.player.name"]

        if assister == player:
            xa += shot["shot.statsbomb_xg"]

    except:
        continue

# =====================================
# PODANIA PROGRESYWNE
# =====================================

progressive = 0

for _, row in passes.iterrows():

    try:

        start_x = row["location"][0]
        end_x = row["pass.end_location"][0]

        if end_x - start_x > 10:
            progressive += 1

    except:
        pass

# =====================================
# KPI W GÓRZE
# =====================================

c1, c2, c3, c4 = st.columns(4)

c1.metric("Podania", len(passes))
c2.metric("Celność podań",
          f"{len(successful_passes)/max(len(passes),1)*100:.1f}%")
c3.metric("xG", round(xg, 2))
c4.metric("xA", round(xa, 2))

st.divider()

c5, c6 = st.columns(2)

c5.metric("Strzały", len(shots))
c6.metric("Podania progresywne", progressive)

# =====================================
# HEATMAPA
# =====================================

st.header("Heatmapa zawodnika")

x = []
y = []

for loc in player_df["location"].dropna():

    try:
        x.append(loc[0])
        y.append(loc[1])

    except:
        pass

pitch = Pitch(pitch_type="statsbomb")

fig, ax = pitch.draw(figsize=(10, 6))

bin_stat = pitch.bin_statistic(
    x,
    y,
    statistic="count",
    bins=(25, 25)
)

pitch.heatmap(
    bin_stat,
    ax=ax,
    cmap="hot"
)

st.pyplot(fig)

# =====================================
# PASS MAP
# =====================================

st.header("Mapa podań")

pitch = Pitch(pitch_type="statsbomb")

fig, ax = pitch.draw(figsize=(10, 6))

for _, row in passes.iterrows():

    try:

        sx = row["location"][0]
        sy = row["location"][1]

        ex = row["pass.end_location"][0]
        ey = row["pass.end_location"][1]

        color = (
            "green"
            if pd.isna(row["pass.outcome.name"])
            else "red"
        )

        pitch.arrows(
            sx,
            sy,
            ex,
            ey,
            color=color,
            ax=ax
        )

    except:
        pass

st.pyplot(fig)
#SHOT MAP

st.header("Mapa strzałów")

pitch = Pitch(
    pitch_type="statsbomb",
    half=True
)

fig, ax = pitch.draw(
    figsize=(10, 6)
)

for _, shot in shots.iterrows():

    try:

        x = shot["location"][0]
        y = shot["location"][1]

        xg_value = shot["shot.statsbomb_xg"]

        goal = (
            shot.get("shot.outcome.name")
            == "Goal"
        )

        pitch.scatter(
            x,
            y,
            s=300 * xg_value + 50,
            ax=ax,
            marker="o"
        )

        if goal:
            ax.text(
                x,
                y,
                "⚽",
                fontsize=12
            )

    except:
        pass

ax.set_title(
    f"Shot Map - {player}"
)

st.pyplot(fig)
# =====================================
# PASSING NETWORK
# =====================================

st.header("Passing Network")

team = player_df["team.name"].dropna().iloc[0]

team_passes = df[
    (df["team.name"] == team)
    &
    (df["type.name"] == "Pass")
]

network = (
    team_passes.groupby(
        [
            "player.name",
            "pass.recipient.name"
        ]
    )
    .size()
    .reset_index(name="count")
)

top_links = network.sort_values(
    "count",
    ascending=False
).head(20)

st.dataframe(top_links)
# RADAR ZAWODNIKA

def player_metrics(df, player_name):

    player_df = df[
        df["player.name"] == player_name
    ]

    passes = player_df[
        player_df["type.name"] == "Pass"
    ]

    shots = player_df[
        player_df["type.name"] == "Shot"
    ]

    xg = shots["shot.statsbomb_xg"].sum()

    xa = 0

    all_shots = df[
        df["type.name"] == "Shot"
    ]

    for _, shot in all_shots.iterrows():

        try:

            assister = shot["pass.player.name"]

            if assister == player_name:
                xa += shot["shot.statsbomb_xg"]

        except:
            pass

    progressive = 0

    for _, row in passes.iterrows():

        try:

            if (
                row["pass.end_location"][0]
                - row["location"][0]
            ) > 10:

                progressive += 1

        except:
            pass

    return {
        "Passes": len(passes),
        "Pass Accuracy":
            len(
                passes[
                    passes["pass.outcome.name"].isna()
                ]
            ) / max(len(passes), 1) * 100,
        "Shots": len(shots),
        "xG": xg,
        "xA": xa,
        "Progressive Passes": progressive
    }

st.header("Radar zawodnika")

metrics = player_metrics(
    df,
    player
)

labels = list(metrics.keys())
values = list(metrics.values())

angles = np.linspace(
    0,
    2 * np.pi,
    len(labels),
    endpoint=False
)

values += values[:1]
angles = np.concatenate(
    (angles, [angles[0]])
)

fig = plt.figure(
    figsize=(8, 8)
)

ax = plt.subplot(
    polar=True
)

ax.plot(
    angles,
    values,
    linewidth=2
)

ax.fill(
    angles,
    values,
    alpha=0.25
)

ax.set_xticks(
    angles[:-1]
)

ax.set_xticklabels(
    labels
)

st.pyplot(fig)
# =====================================
# SUROWE DANE
# =====================================

with st.expander("Pokaż dane zawodnika"):
    st.dataframe(player_df)