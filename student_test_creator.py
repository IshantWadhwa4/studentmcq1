import streamlit as st
import openai
import json
import re
import time
import random
from datetime import datetime
from syllabus import syllabus

def get_topics_for_subject(subject):
    """Get topics for a given subject from syllabus"""
    if subject in syllabus:
        return list(syllabus[subject].keys())
    return []

def create_openai_prompt(subject, topics, additional_info, num_questions, level, syllabus_data):
    """Create a detailed prompt for OpenAI to generate MCQs"""
    
    # Get syllabus information for selected topics
    topic_descriptions = ""
    for topic in topics:
        if topic in syllabus_data[subject]:
            topic_descriptions += f"\n- {topic}: {syllabus_data[subject][topic]['description']}"
            topic_descriptions += f"\n  Past Questions Pattern: {syllabus_data[subject][topic]['past_questions']}"
    
    prompt = f"""
Generate {num_questions} multiple-choice questions (MCQs) for {subject} examination.

SUBJECT: {subject}

TOPICS TO COVER:
{topic_descriptions}

ADDITIONAL REQUIREMENTS:
{additional_info if additional_info else "None"}

DIFFICULTY LEVEL: {level}
- If Easy: Focus on direct application of formulas and basic concepts
- If Medium: Require 2-3 step problem solving and concept understanding
- If Hard: Complex multi-step problems requiring deep understanding and multiple concept integration

INSTRUCTIONS:
1. Generate exactly {num_questions} questions and make sure donot repeat any question.
2. Each question should have exactly 4 options (A, B, C, D)
3. Only one option should be correct
4. Questions should be educational and test understanding
5. Include numerical problems, conceptual questions, and application-based questions
6. Ensure questions are unambiguous and have clear correct answers
7. Provide detailed explanations for correct answers
8. Make questions suitable for high school level students

FORMAT YOUR RESPONSE AS JSON:
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Question text here",
      "options": {{
        "A": "Option A text",
        "B": "Option B text", 
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Detailed explanation of why this answer is correct",
      "topic": "Specific topic from the syllabus",
      "difficulty": "{level}"
    }}
  ]
}}

Make sure the JSON is properly formatted and can be parsed.
"""
    return prompt

def generate_mcqs(api_key, prompt):
    """Generate MCQs using OpenAI API"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert examination question creator. Generate high-quality multiple-choice questions following the exact format requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

def parse_mcq_response(response_text):
    """Parse the OpenAI response to extract MCQ data"""
    try:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group()
            mcq_data = json.loads(json_text)
            return mcq_data
        else:
            st.error("Could not find valid JSON in the response")
            return None
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON response: {str(e)}")
        return None

def display_question(question, question_num, total_questions):
    """Display a single question with options"""
    st.markdown(f"### Question {question_num} of {total_questions}")
    st.write(question['question_text'])
    
    # Display options
    option_key = f"q_{question_num}"
    selected_answer = st.radio(
        "Choose your answer:",
        options=list(question['options'].keys()),
        format_func=lambda x: f"{x}. {question['options'][x]}",
        key=option_key
    )
    
    return selected_answer

def calculate_score(questions, student_answers):
    """Calculate score and generate results"""
    total_questions = len(questions)
    correct_answers = 0
    results = []
    
    for i, question in enumerate(questions):
        question_num = i + 1
        student_answer = student_answers.get(f"q_{question_num}")
        correct_answer = question['correct_answer']
        is_correct = student_answer == correct_answer
        
        if is_correct:
            correct_answers += 1
        
        result = {
            "question_number": question_num,
            "question_text": question['question_text'],
            "options": question['options'],
            "student_answer": student_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get('explanation', 'No explanation provided'),
            "topic": question.get('topic', 'General'),
            "difficulty": question.get('difficulty', 'Medium')
        }
        results.append(result)
    
    score_percentage = (correct_answers / total_questions) * 100
    
    return {
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "score_percentage": score_percentage,
        "results": results
    }

def display_results(score_data, student_name):
    """Display test results with explanations"""
    st.header("📊 Test Results")
    
    # Score summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Score", f"{score_data['score_percentage']:.1f}%")
    with col2:
        st.metric("Correct", f"{score_data['correct_answers']}/{score_data['total_questions']}")
    with col3:
        st.metric("Incorrect", f"{score_data['total_questions'] - score_data['correct_answers']}")
    
    # Performance indicator
    if score_data['score_percentage'] >= 80:
        st.success(f"🎉 Excellent performance, {student_name}! Keep up the great work!")
    elif score_data['score_percentage'] >= 60:
        st.info(f"👍 Good job, {student_name}! There's room for improvement.")
    else:
        st.warning(f"📚 Keep studying, {student_name}! You can do better next time.")
    
    # Detailed results
    st.header("📋 Detailed Results")
    
    for result in score_data['results']:
        if result['is_correct']:
            st.success(f"✅ Question {result['question_number']}: Correct")
        else:
            st.error(f"❌ Question {result['question_number']}: Incorrect")
        
        with st.expander(f"View Question {result['question_number']} Details"):
            st.write(f"**Question:** {result['question_text']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Options:**")
                for opt_key, opt_text in result['options'].items():
                    if opt_key == result['correct_answer']:
                        st.write(f"✅ **{opt_key}.** {opt_text}")
                    elif opt_key == result['student_answer']:
                        st.write(f"❌ **{opt_key}.** {opt_text} (Your Answer)")
                    else:
                        st.write(f"   **{opt_key}.** {opt_text}")
            
            with col2:
                st.write(f"**Your Answer:** {result['student_answer'] or 'Not answered'}")
                st.write(f"**Correct Answer:** {result['correct_answer']}")
                st.write(f"**Topic:** {result['topic']}")
                st.write(f"**Difficulty:** {result['difficulty']}")
            
            st.write(f"**Explanation:** {result['explanation']}")

def main():
    st.set_page_config(
        page_title="Student Test Creator",
        page_icon="👨‍🎓",
        layout="wide"
    )
    
    st.title("👨‍🎓 Student Test Creator")
    st.markdown("Create your own tests, take them instantly, and get detailed results!")
    
    # Initialize session state
    if 'test_created' not in st.session_state:
        st.session_state.test_created = False
    if 'test_data' not in st.session_state:
        st.session_state.test_data = None
    if 'test_started' not in st.session_state:
        st.session_state.test_started = False
    if 'test_completed' not in st.session_state:
        st.session_state.test_completed = False
    if 'student_answers' not in st.session_state:
        st.session_state.student_answers = {}
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'student_name' not in st.session_state:
        st.session_state.student_name = ""
    
    # Show appropriate interface based on state
    if not st.session_state.test_created:
        show_test_creation_interface()
    elif not st.session_state.test_started:
        show_test_start_interface()
    elif not st.session_state.test_completed:
        show_test_interface()
    else:
        show_results_interface()

def show_test_creation_interface():
    """Show the test creation interface"""
    st.header("🎯 Create Your Test")
    
    # Student name input
    student_name = st.text_input(
        "Your Name:",
        placeholder="Enter your name",
        help="Your name will appear on the test results"
    )
    
    # Subject selection
    subjects = list(syllabus.keys())
    selected_subject = st.selectbox(
        "Select Subject:",
        subjects,
        help="Choose the subject for your test"
    )
    
    # Topics selection
    available_topics = get_topics_for_subject(selected_subject)
    if available_topics:
        selected_topics = st.multiselect(
            "Select Topics:",
            available_topics,
            help="Choose specific topics to focus on"
        )
    else:
        st.warning("No topics available for this subject.")
        selected_topics = []
    
    # Additional information
    additional_info = st.text_area(
        "Additional Information (Optional):",
        placeholder="Enter any specific requirements or focus areas...",
        help="Provide any additional context for your test"
    )
    
    # Number of questions
    num_questions = st.slider(
        "Number of Questions:",
        min_value=5,
        max_value=25,
        value=10,
        help="Select how many questions you want in your test"
    )
    
    # Difficulty level
    difficulty_level = st.selectbox(
        "Difficulty Level:",
        ["Easy", "Medium", "Hard"],
        index=1,
        help="Choose the difficulty level for your test"
    )
    
    # OpenAI API Key
    api_key = st.text_input(
        "OpenAI API Key:",
        type="password",
        help="Enter your OpenAI API key to generate questions"
    )
    
    # Generate test button
    if st.button("🚀 Create My Test", type="primary"):
        if not student_name:
            st.error("Please enter your name")
            return
        
        if not api_key:
            st.error("Please provide your OpenAI API key")
            return
        
        if not selected_topics:
            st.error("Please select at least one topic")
            return
        
        # Store student name
        st.session_state.student_name = student_name
        
        # Show loading spinner
        with st.spinner("Creating your test... This may take a few moments."):
            # Create prompt
            prompt = create_openai_prompt(
                selected_subject, 
                selected_topics, 
                additional_info, 
                num_questions, 
                difficulty_level, 
                syllabus
            )
            
            # Generate MCQs
            response = generate_mcqs(api_key, prompt)
            
            if response:
                # Parse response
                mcq_data = parse_mcq_response(response)
                
                if mcq_data:
                    # Store test data
                    st.session_state.test_data = mcq_data
                    st.session_state.test_created = True
                    st.rerun()
                else:
                    st.error("Failed to create test. Please try again.")
            else:
                st.error("Failed to generate questions. Please check your API key and try again.")

def show_test_start_interface():
    """Show the test start interface"""
    st.header(f"🎯 Test Ready for {st.session_state.student_name}")
    
    if st.session_state.test_data:
        num_questions = len(st.session_state.test_data['questions'])
        st.info(f"Your test has {num_questions} questions. Once you start, you'll go through each question one by one.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝 Start Test", type="primary"):
                st.session_state.test_started = True
                st.session_state.current_question = 0
                st.rerun()
        
        with col2:
            if st.button("🔄 Create New Test"):
                # Reset all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

def show_test_interface():
    """Show the test taking interface"""
    if not st.session_state.test_data:
        st.error("No test data available")
        return
    
    questions = st.session_state.test_data['questions']
    current_q = st.session_state.current_question
    total_questions = len(questions)
    
    # Progress bar
    progress = (current_q + 1) / total_questions
    st.progress(progress)
    
    # Display current question
    if current_q < total_questions:
        question = questions[current_q]
        
        st.markdown(f"### Question {current_q + 1} of {total_questions}")
        st.write(question['question_text'])
        
        # Display options
        option_key = f"current_answer"
        selected_answer = st.radio(
            "Choose your answer:",
            options=list(question['options'].keys()),
            format_func=lambda x: f"{x}. {question['options'][x]}",
            key=option_key
        )
        
        # Navigation buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if current_q > 0:
                if st.button("⬅️ Previous"):
                    # Save current answer
                    if selected_answer:
                        st.session_state.student_answers[f"q_{current_q + 1}"] = selected_answer
                    st.session_state.current_question = current_q - 1
                    st.rerun()
        
        with col2:
            if current_q < total_questions - 1:
                if st.button("Next ➡️"):
                    # Save current answer
                    if selected_answer:
                        st.session_state.student_answers[f"q_{current_q + 1}"] = selected_answer
                    st.session_state.current_question = current_q + 1
                    st.rerun()
        
        with col3:
            if current_q == total_questions - 1:
                if st.button("🏁 Finish Test", type="primary"):
                    # Save current answer
                    if selected_answer:
                        st.session_state.student_answers[f"q_{current_q + 1}"] = selected_answer
                    st.session_state.test_completed = True
                    st.rerun()
        
        # Show current answer if previously selected
        if f"q_{current_q + 1}" in st.session_state.student_answers:
            st.info(f"Previously selected: {st.session_state.student_answers[f'q_{current_q + 1}']}")

def show_results_interface():
    """Show the test results interface"""
    if not st.session_state.test_data:
        st.error("No test data available")
        return
    
    # Calculate score
    score_data = calculate_score(
        st.session_state.test_data['questions'], 
        st.session_state.student_answers
    )
    
    # Display results
    display_results(score_data, st.session_state.student_name)
    
    # Option to take another test
    st.markdown("---")
    if st.button("🔄 Create Another Test", type="primary"):
        # Reset all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if __name__ == "__main__":
    main() 