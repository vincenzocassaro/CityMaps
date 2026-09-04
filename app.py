from pathlib import Path

import streamlit as st

import prettymaps
from citymaps import RenderError, RenderRequest, render_city_map


PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"

st.set_page_config(
    page_title="CityMaps studio",
    page_icon="🗺️",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --city-ink: #1d1048;
        --city-pink: #ff55ae;
        --city-butter: #ffdc8c;
        --city-lilac: #eee9ff;
        --city-paper: #fbfaff;
    }
    .stApp {
        color: var(--city-ink);
        background:
            radial-gradient(circle at 86% 12%, rgba(255, 85, 174, .12), transparent 24rem),
            radial-gradient(circle at 8% 90%, rgba(116, 205, 194, .18), transparent 30rem),
            var(--city-paper);
    }
    .block-container { max-width: 1180px; padding-top: 2.25rem; }
    .city-kicker {
        color: #6c5c96;
        font: 700 .76rem/1.2 "IBM Plex Mono", ui-monospace, monospace;
        letter-spacing: .16em;
        text-transform: uppercase;
    }
    .city-title {
        max-width: 840px;
        margin: .35rem 0 .45rem;
        color: var(--city-ink);
        font: 800 clamp(3rem, 8vw, 6.6rem)/.88 "Avenir Next", Avenir, sans-serif;
        letter-spacing: -.07em;
    }
    .city-title span { color: var(--city-pink); }
    .city-intro {
        max-width: 650px;
        margin: 0 0 2.4rem;
        color: #594d78;
        font: 500 1.05rem/1.55 "Avenir Next", Avenir, sans-serif;
    }
    [data-testid="stForm"] {
        padding: 1.5rem 1.5rem .7rem;
        border: 1px solid rgba(29, 16, 72, .12);
        border-radius: 22px;
        background: rgba(255, 255, 255, .78);
        box-shadow: 0 20px 60px rgba(29, 16, 72, .07);
    }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        min-height: 3.2rem;
        border: 0;
        border-radius: 999px;
        color: var(--city-ink);
        background: var(--city-butter);
        font-weight: 800;
        box-shadow: 0 8px 0 var(--city-ink);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        color: var(--city-ink);
        background: #ffe7aa;
        transform: translateY(2px);
        box-shadow: 0 6px 0 var(--city-ink);
    }
    .stDownloadButton > button { border-radius: 999px; font-weight: 700; }
    [data-testid="stVideo"], [data-testid="stImage"] img { border-radius: 18px; }
    .city-empty {
        min-height: 430px;
        display: grid;
        place-items: center;
        padding: 3rem;
        border: 1px dashed rgba(29, 16, 72, .24);
        border-radius: 22px;
        color: #746990;
        text-align: center;
        background: rgba(238, 233, 255, .38);
    }
    @media (prefers-reduced-motion: reduce) {
        .stButton > button, [data-testid="stFormSubmitButton"] > button { transition: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="city-kicker">CityMaps studio · one-step renderer</div>', unsafe_allow_html=True)
st.markdown('<h1 class="city-title">Draw a city.<br><span>Watch it appear.</span></h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="city-intro">Choose a place and CityMaps handles the map, line animation, video encoding, and final still frame.</p>',
    unsafe_allow_html=True,
)

controls, preview = st.columns([0.86, 1.14], gap="large")

with controls:
    presets = prettymaps.presets()["preset"].tolist()
    default_preset = presets.index("default") if "default" in presets else 0

    with st.form("citymap-request"):
        st.subheader("Map direction")
        location = st.text_area(
            "Location",
            value="Stad van de Zon, Heerhugowaard, Netherlands",
            height=88,
            help="A city, neighbourhood, landmark, or full address.",
        )

        first, second = st.columns(2)
        with first:
            preset = st.selectbox("Map style", presets, index=default_preset)
        with second:
            format_name = st.selectbox("Video format", ["Portrait", "Square"])

        with st.expander("Fine-tune", expanded=False):
            radius_m = st.slider("Radius", 300, 2000, 750, 50, format="%d m")
            circular = st.checkbox("Circular map")
            animation_seconds = st.slider("Drawing time", 5, 30, 15, 1, format="%d sec")
            hold_seconds = st.slider("Final still", 0, 10, 3, 1, format="%d sec")
            st.caption("Building palette")
            palette_columns = st.columns(2)
            with palette_columns[0]:
                color_one = st.color_picker("Colour one", "#433633")
            with palette_columns[1]:
                color_two = st.color_picker("Colour two", "#FF5E5B")

        submitted = st.form_submit_button(
            "Generate animated map",
            type="primary",
            width="stretch",
        )

    st.caption("Map data © OpenStreetMap contributors · rendering by Prettymaps")

if submitted:
    dimensions = (1080, 1080) if format_name == "Square" else (992, 1380)
    request = RenderRequest(
        location=location,
        radius_m=radius_m,
        preset=preset,
        circular=circular,
        palette=(color_one, color_two),
        animation_seconds=animation_seconds,
        hold_seconds=hold_seconds,
        output_width=dimensions[0],
        output_height=dimensions[1],
    )

    with controls:
        with st.status("Building your CityMap", expanded=True) as status:
            try:
                result = render_city_map(request, OUTPUT_DIR, on_stage=status.write)
                st.session_state["citymaps_result"] = {
                    "name": result.name,
                    "video": result.video_path.read_bytes(),
                    "png": result.png_path.read_bytes(),
                    "svg": result.svg_path.read_bytes(),
                }
                status.update(label="CityMap ready", state="complete", expanded=False)
            except (RenderError, ValueError) as error:
                status.update(label="CityMap could not be generated", state="error")
                st.error(str(error))

with preview:
    artifact = st.session_state.get("citymaps_result")
    if artifact:
        st.video(artifact["video"])
        st.subheader(artifact["name"].replace("-", " ").title())
        video_download, source_downloads = st.columns([1.1, .9])
        with video_download:
            st.download_button(
                "Download MP4",
                artifact["video"],
                file_name=f"{artifact['name']}.mp4",
                mime="video/mp4",
                type="primary",
                width="stretch",
            )
        with source_downloads:
            with st.popover("Source files", width="stretch"):
                st.download_button(
                    "Download PNG",
                    artifact["png"],
                    file_name=f"{artifact['name']}.png",
                    mime="image/png",
                    width="stretch",
                )
                st.download_button(
                    "Download SVG",
                    artifact["svg"],
                    file_name=f"{artifact['name']}.svg",
                    mime="image/svg+xml",
                    width="stretch",
                )
    else:
        st.markdown(
            '<div class="city-empty"><div><strong>Your animated map will appear here.</strong><br>Start with a location on the left.</div></div>',
            unsafe_allow_html=True,
        )
