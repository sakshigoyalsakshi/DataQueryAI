import pandas as pd
import streamlit as st

from data.csv_manager import delete_file, get_preview, list_user_files, store_csv


def show_upload_page(user_id: str) -> None:
    st.header("My Datasets")

    # Upload section
    with st.expander("Upload a new CSV", expanded=True):
        uploaded = st.file_uploader("Choose a CSV file (max 10 MB)", type=["csv"])
        if uploaded:
            if uploaded.size > 10 * 1024 * 1024:
                st.error("File exceeds 10 MB limit.")
            else:
                with st.spinner("Loading and storing CSV..."):
                    try:
                        df = pd.read_csv(uploaded)
                        if df.empty or len(df.columns) == 0:
                            st.error("CSV appears to be empty or has no columns.")
                        else:
                            meta = store_csv(user_id, uploaded.name, df)
                            st.success(
                                f"Uploaded **{uploaded.name}** — {meta['row_count']:,} rows, "
                                f"{len(meta['columns_info'])} columns"
                            )
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to parse CSV: {e}")

    st.divider()

    # List user files
    files = list_user_files(user_id)
    if not files:
        st.info("No datasets yet. Upload a CSV above to get started.")
        return

    for f in files:
        col1, col2 = st.columns([4, 1])
        with col1:
            cols = [c["name"] for c in f["columns_info"]]
            st.markdown(f"**{f['filename']}** — {f['row_count']:,} rows")
            st.caption(f"Columns: {', '.join(cols)}")
        with col2:
            if st.button("Delete", key=f"del_{f['id']}", type="secondary"):
                delete_file(user_id, f["id"])
                st.rerun()

        with st.expander(f"Preview: {f['filename']}", expanded=False):
            preview_df = get_preview(f["table_name"])
            st.dataframe(preview_df, use_container_width=True)
