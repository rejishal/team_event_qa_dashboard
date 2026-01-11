import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Team Quiz Dashboard",
    page_icon="🎯",
    layout="wide"
)

# Data persistence file
DATA_FILE = "quiz_data.json"

def load_data():
    """Load data from file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                return data
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
    return {
        'teams': [],
        'rounds': [],
        'questions': {},
        'scores': {}
    }

def save_data():
    """Save data to file"""
    try:
        data = {
            'teams': st.session_state.teams,
            'rounds': st.session_state.rounds,
            'questions': st.session_state.questions,
            'scores': st.session_state.scores
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

# Initialize session state
if 'initialized' not in st.session_state:
    loaded_data = load_data()
    st.session_state.teams = loaded_data.get('teams', [])
    st.session_state.rounds = loaded_data.get('rounds', [])
    st.session_state.questions = loaded_data.get('questions', {})
    st.session_state.scores = loaded_data.get('scores', {})
    st.session_state.current_round = None
    st.session_state.initialized = True

def add_team(team_name):
    if team_name and team_name not in st.session_state.teams:
        st.session_state.teams.append(team_name)
        save_data()
        return True
    return False

def remove_team(team_name):
    if team_name in st.session_state.teams:
        st.session_state.teams.remove(team_name)
        # Also remove from all rounds
        for round_name in st.session_state.rounds:
            if team_name in st.session_state.scores[round_name]['team_scores']:
                del st.session_state.scores[round_name]['team_scores'][team_name]
        save_data()
        return True
    return False

def add_round(round_name, qualifying_teams):
    if round_name and round_name not in st.session_state.rounds:
        st.session_state.rounds.append(round_name)
        st.session_state.questions[round_name] = []
        st.session_state.scores[round_name] = {
            'qualifying_teams': qualifying_teams,
            'team_scores': {}
        }
        save_data()
        return True
    return False

def add_question(round_name, question_text, marks):
    if round_name in st.session_state.questions:
        question_id = len(st.session_state.questions[round_name]) + 1
        st.session_state.questions[round_name].append({
            'id': question_id,
            'text': question_text,
            'marks': marks
        })
        save_data()
        return True
    return False

def remove_question(round_name, question):
    if round_name in st.session_state.questions:
        st.session_state.questions[round_name].remove(question)
        # Reindex questions
        for i, q in enumerate(st.session_state.questions[round_name], 1):
            q['id'] = i
        save_data()
        return True
    return False

def calculate_rankings(round_name):
    if round_name not in st.session_state.scores:
        return []
    
    team_scores = st.session_state.scores[round_name]['team_scores']
    rankings = []
    
    for team, scores in team_scores.items():
        total = sum(scores.values())
        rankings.append({'team': team, 'total': total})
    
    rankings.sort(key=lambda x: x['total'], reverse=True)
    
    for i, rank in enumerate(rankings):
        rank['position'] = i + 1
    
    return rankings

def get_qualified_teams(round_name):
    rankings = calculate_rankings(round_name)
    qualifying_count = st.session_state.scores[round_name]['qualifying_teams']
    
    if qualifying_count == -1:
        return [r['team'] for r in rankings]
    
    return [r['team'] for r in rankings[:qualifying_count]]

def save_scores(round_name, team_name, scores):
    st.session_state.scores[round_name]['team_scores'][team_name] = scores
    save_data()

# Sidebar navigation
st.sidebar.title("🎯 Quiz Dashboard")

# Add data status indicator
if os.path.exists(DATA_FILE):
    file_time = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
    st.sidebar.info(f"📊 Last saved: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")

page = st.sidebar.radio("Navigation", 
                        ["Setup", "Manage Questions", "Score Entry", "Leaderboard", "Export/Reset"])

# SETUP PAGE
if page == "Setup":
    st.title("Quiz Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Team Management")
        with st.form("add_team_form"):
            team_name = st.text_input("Team Name")
            submit_team = st.form_submit_button("Add Team")
            
            if submit_team:
                if add_team(team_name):
                    st.success(f"Team '{team_name}' added!")
                    st.rerun()
                else:
                    st.error("Team already exists or invalid name")
        
        if st.session_state.teams:
            st.write("**Current Teams:**")
            for i, team in enumerate(st.session_state.teams, 1):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.write(f"{i}. {team}")
                with col_b:
                    if st.button("❌", key=f"del_team_{i}"):
                        remove_team(team)
                        st.rerun()
    
    with col2:
        st.subheader("Round Management")
        
        if not st.session_state.teams:
            st.warning("Please add teams first before creating rounds!")
        else:
            with st.form("add_round_form"):
                round_name = st.text_input("Round Name")
                
                st.write("**Select Team Source:**")
                if st.session_state.rounds:
                    team_source = st.radio(
                        "Choose teams from:",
                        ["All Teams", "Previous Round Winners", "Custom Selection"],
                        horizontal=True
                    )
                    
                    if team_source == "Previous Round Winners":
                        prev_round = st.selectbox(
                            "Select previous round:",
                            st.session_state.rounds
                        )
                else:
                    team_source = st.radio(
                        "Choose teams from:",
                        ["All Teams", "Custom Selection"],
                        horizontal=True
                    )
                
                # Team selection based on source
                if team_source == "All Teams":
                    available_teams = st.session_state.teams.copy()
                    selected_teams = st.multiselect(
                        "Participating Teams (all selected by default):",
                        available_teams,
                        default=available_teams
                    )
                elif team_source == "Custom Selection":
                    available_teams = st.session_state.teams.copy()
                    selected_teams = st.multiselect(
                        "Select teams for this round:",
                        available_teams
                    )
                else:  # Previous Round Winners
                    qualified_teams = get_qualified_teams(prev_round)
                    st.info(f"Qualified teams from {prev_round}: {', '.join(qualified_teams)}")
                    selected_teams = st.multiselect(
                        "Participating Teams:",
                        qualified_teams,
                        default=qualified_teams
                    )
                
                qualifying_teams = st.number_input(
                    "Teams qualifying for next round (-1 for all)",
                    min_value=-1,
                    value=-1,
                    step=1
                )
                
                submit_round = st.form_submit_button("Add Round")
                
                if submit_round:
                    if not selected_teams:
                        st.error("Please select at least one team for this round!")
                    elif add_round(round_name, int(qualifying_teams)):
                        for team in selected_teams:
                            st.session_state.scores[round_name]['team_scores'][team] = {}
                        save_data()
                        st.success(f"Round '{round_name}' added with {len(selected_teams)} teams!")
                        st.rerun()
                    else:
                        st.error("Round already exists or invalid name")
        
        if st.session_state.rounds:
            st.write("**Current Rounds:**")
            for i, round_name in enumerate(st.session_state.rounds, 1):
                num_teams = len(st.session_state.scores[round_name]['team_scores'])
                num_questions = len(st.session_state.questions[round_name])
                st.write(f"{i}. {round_name} ({num_teams} teams, {num_questions} questions)")

# MANAGE QUESTIONS PAGE
elif page == "Manage Questions":
    st.title("Manage Questions")
    
    if not st.session_state.rounds:
        st.warning("Please add at least one round first!")
    else:
        selected_round = st.selectbox("Select Round", st.session_state.rounds)
        
        st.subheader(f"Questions for {selected_round}")
        
        with st.form("add_question_form"):
            question_text = st.text_area("Question Text")
            marks = st.number_input("Marks", min_value=1, value=10, step=1)
            submit_question = st.form_submit_button("Add Question")
            
            if submit_question:
                if question_text.strip():
                    if add_question(selected_round, question_text, int(marks)):
                        st.success("Question added!")
                        st.rerun()
                else:
                    st.error("Question text cannot be empty")
        
        st.divider()
        
        if st.session_state.questions[selected_round]:
            st.write("**Current Questions:**")
            for q in st.session_state.questions[selected_round]:
                col1, col2, col3 = st.columns([1, 6, 1])
                with col1:
                    st.write(f"**Q{q['id']}**")
                with col2:
                    st.write(f"{q['text']} ({q['marks']} marks)")
                with col3:
                    if st.button("🗑️", key=f"del_q_{selected_round}_{q['id']}"):
                        remove_question(selected_round, q)
                        st.rerun()
        else:
            st.info("No questions added yet for this round")

# SCORE ENTRY PAGE
elif page == "Score Entry":
    st.title("Score Entry")
    
    if not st.session_state.rounds:
        st.warning("Please add at least one round first!")
    else:
        selected_round = st.selectbox("Select Round", st.session_state.rounds)
        
        if not st.session_state.questions[selected_round]:
            st.warning(f"Please add questions for {selected_round} first!")
        else:
            st.subheader(f"Score Entry for {selected_round}")
            
            teams = list(st.session_state.scores[selected_round]['team_scores'].keys())
            
            if not teams:
                st.warning("No teams participating in this round!")
            else:
                selected_team = st.selectbox("Select Team", teams)
                
                st.write(f"### Scoring for {selected_team}")
                
                with st.form("score_entry_form"):
                    scores = {}
                    for q in st.session_state.questions[selected_round]:
                        current_score = st.session_state.scores[selected_round]['team_scores'][selected_team].get(q['id'], 0)
                        score = st.number_input(
                            f"Q{q['id']}: {q['text'][:50]}... (Max: {q['marks']})",
                            min_value=0,
                            max_value=q['marks'],
                            value=current_score,
                            key=f"score_{q['id']}"
                        )
                        scores[q['id']] = score
                    
                    submit_scores = st.form_submit_button("Save Scores")
                    
                    if submit_scores:
                        save_scores(selected_round, selected_team, scores)
                        st.success(f"Scores saved for {selected_team}!")
                        st.rerun()

# LEADERBOARD PAGE
elif page == "Leaderboard":
    st.title("Leaderboard")
    
    if not st.session_state.rounds:
        st.warning("Please add at least one round first!")
    else:
        selected_round = st.selectbox("Select Round", st.session_state.rounds)
        
        st.subheader(f"Leaderboard - {selected_round}")
        
        rankings = calculate_rankings(selected_round)
        
        if rankings:
            df = pd.DataFrame(rankings)
            df.index = df.index + 1
            
            st.dataframe(
                df,
                column_config={
                    "position": st.column_config.NumberColumn("Rank", format="%d"),
                    "team": "Team Name",
                    "total": st.column_config.NumberColumn("Total Score", format="%d")
                },
                hide_index=False,
                use_container_width=True
            )
            
            qualifying_count = st.session_state.scores[selected_round]['qualifying_teams']
            if qualifying_count > 0:
                qualified = [r['team'] for r in rankings[:qualifying_count]]
                st.success(f"**Teams qualifying for next round:** {', '.join(qualified)}")
            
            st.divider()
            st.subheader("Detailed Scores")
            
            for rank in rankings:
                with st.expander(f"{rank['position']}. {rank['team']} - {rank['total']} points"):
                    team_scores = st.session_state.scores[selected_round]['team_scores'][rank['team']]
                    
                    score_details = []
                    for q in st.session_state.questions[selected_round]:
                        score_details.append({
                            'Question': f"Q{q['id']}",
                            'Text': q['text'][:50] + "...",
                            'Score': f"{team_scores.get(q['id'], 0)}/{q['marks']}"
                        })
                    
                    if score_details:
                        st.table(pd.DataFrame(score_details))
        else:
            st.info("No scores entered yet for this round")

# EXPORT/RESET DATA PAGE
elif page == "Export/Reset":
    st.title("Export & Reset Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Export Data")
        
        export_data = {
            'teams': st.session_state.teams,
            'rounds': st.session_state.rounds,
            'questions': st.session_state.questions,
            'scores': st.session_state.scores
        }
        
        st.download_button(
            label="Download Quiz Data (JSON)",
            data=json.dumps(export_data, indent=2),
            file_name=f"quiz_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        st.divider()
        
        st.subheader("📤 Import Data")
        uploaded_file = st.file_uploader("Upload Quiz Data (JSON)", type=['json'])
        
        if uploaded_file is not None:
            if st.button("Import Data"):
                try:
                    imported_data = json.load(uploaded_file)
                    st.session_state.teams = imported_data.get('teams', [])
                    st.session_state.rounds = imported_data.get('rounds', [])
                    st.session_state.questions = imported_data.get('questions', {})
                    st.session_state.scores = imported_data.get('scores', {})
                    save_data()
                    st.success("Data imported successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error importing data: {str(e)}")
    
    with col2:
        st.subheader("📊 Summary Statistics")
        
        total_questions = sum(len(questions) for questions in st.session_state.questions.values())
        
        st.metric("Total Teams", len(st.session_state.teams))
        st.metric("Total Rounds", len(st.session_state.rounds))
        st.metric("Total Questions", total_questions)
        
        st.divider()
        
        st.subheader("⚠️ Reset Data")
        st.warning("This will permanently delete all quiz data!")
        
        if st.button("🗑️ Reset All Data", type="primary"):
            if st.checkbox("I understand this cannot be undone"):
                st.session_state.teams = []
                st.session_state.rounds = []
                st.session_state.questions = {}
                st.session_state.scores = {}
                save_data()
                st.success("All data has been reset!")
                st.rerun()