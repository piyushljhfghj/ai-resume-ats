# dashboard.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from app.intelligent_ranker import rank_resumes
from app.report_generator import generate_pdf_report

st.set_page_config(
    page_title="AI Resume Screening System",
    layout="wide"
)

st.title("🤖 Intelligent AI Resume Screening System")
st.caption("Enterprise-Level ATS | Phase 6 Professional Dashboard")

jd_text = st.text_area("📌 Paste Job Description Here", height=200)

uploaded_files = st.file_uploader(
    "📄 Upload Resumes (.txt or .pdf)",
    type=["txt", "pdf"],
    accept_multiple_files=True
)

if st.button("🚀 Run Screening"):

    if not jd_text.strip():
        st.warning("Please enter a Job Description")
        st.stop()

    if not uploaded_files:
        st.warning("Please upload at least one resume")
        st.stop()

    with st.spinner("Analyzing resumes..."):
        results = rank_resumes(jd_text, uploaded_files)

    df = pd.DataFrame(results)
    df = df.sort_values(by="final_score", ascending=False)

    st.success("🏆 Screening Complete")

 # EXECUTIVE HIRING INSIGHTS


    st.markdown("## 📊 Hiring Insights")

    colA, colB, colC = st.columns(3)

    avg_score = df["final_score"].mean()
    top_score = df["final_score"].max()
    total_candidates = len(df)

    colA.metric("Average Score", f"{round(avg_score,1)}%")
    colB.metric("Top Candidate Score", f"{round(top_score,1)}%")
    colC.metric("Total Candidates", total_candidates)

    st.markdown("---")

   
    #  Analytics Grid (2 Column Layout)

    left, right = st.columns(2)

    # Candidate Score Chart
    with left:
        st.markdown("### 📈 Final Score Comparison")

        fig1, ax1 = plt.subplots(figsize=(6,4))
        ax1.barh(df["filename"], df["final_score"])
        ax1.set_xlabel("Final Score (%)")
        ax1.set_ylabel("Candidate")
        ax1.set_xlim(0, 100)
        plt.tight_layout()
        st.pyplot(fig1)

    
    # Skill Distribution
    
    with right:
        st.markdown("### 📊 Skill Score Distribution")

        fig2, ax2 = plt.subplots(figsize=(6,4))
        ax2.hist(df["skill_score"], bins=5)
        ax2.set_xlabel("Skill Score")
        ax2.set_ylabel("Number of Candidates")
        plt.tight_layout()
        st.pyplot(fig2)

    st.markdown("---")

    
    #  Skill Gap Heatmap (Compact)
    st.markdown("### 🔥 Skill Gap Overview")

    df["missing_count"] = df["missing_skills"].apply(lambda x: len(x))

    heatmap_data = df[["missing_count"]]

    fig3, ax3 = plt.subplots(figsize=(4,1.8))
    sns.heatmap(
        heatmap_data,
        annot=True,
        cmap="Reds",
        yticklabels=df["filename"],
        xticklabels=["Missing Skills"],
        cbar=False,
        linewidth=0.5
    )

    ax3.tick_params(labelsize=8)
    plt.tight_layout()

    st.pyplot(fig3)

    
    #  Candidate Comparison Table
    
    st.markdown("### 📋 Candidate Comparison")

    comparison_df = df[
        ["filename", "semantic_score", "skill_score", "experience_score", "final_score"]
    ]

    st.dataframe(comparison_df, use_container_width=True)

    
    #  Export Results

    st.markdown("### 💾 Export Screening Results")

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Results (CSV)",
        data=csv,
        file_name="screening_results.csv",
        mime="text/csv"
    )

    st.markdown("---")

    
    # 🏆 INDIVIDUAL REPORTS

    for i, result in enumerate(results):

        st.markdown("---")

        if i == 0:
            st.markdown("## 🌟 Best Match")

        st.markdown(f"### 🏆 Rank {i+1} — {result['filename']}")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Semantic", f"{result['semantic_score']}%")
        col2.metric("Skill", f"{result['skill_score']}%")
        col3.metric("Experience", f"{result['experience_score']}%")
        col4.metric("Final Score", f"{result['final_score']}%")

        st.progress(result["final_score"] / 100)

        st.write("**Matched Skills:**")
        st.write(", ".join(result["matched_skills"]) if result["matched_skills"] else "None")

        st.write("**Missing Skills:**")
        st.write(", ".join(result["missing_skills"]) if result["missing_skills"] else "None")

        st.write("**AI Summary:**")
        st.write(result["explanation"])

    # 📥 PDF Downloads
    

    st.markdown("## 📥 Download Individual Reports")

    for result in results:
        pdf_bytes = generate_pdf_report(result)

        st.download_button(
            label=f"Download {result['filename']} Report",
            data=pdf_bytes,
            file_name=f"{result['filename']}_report.pdf",
            mime="application/pdf",
            key=result["filename"]
        )