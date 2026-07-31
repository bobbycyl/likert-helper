import streamlit as st

pg_generator = st.Page("./pages/1_Generator.py")
pg_calculator = st.Page("./pages/2_Calculator.py")
pg_test = st.Page("./pages/3_Test.py")
pg_list = [pg_generator, pg_calculator, pg_test]
pg = st.navigation(pg_list)
pg.run()
