from pyexpat import features
import streamlit as st
import pandas as pd
import plotly.express as px
from dateutil import tz
import os
import json
from zipfile import ZipFile
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt


header = st.container()
dataset = st.container()
compare_two_chat_histories = st.container()
heatmap2d = st.container()
wordcloud_countainer = st.container()

#Add a sidebar
st.sidebar.subheader("Visualization Settings")

# Setup file upload:
uploaded_file = st.sidebar.file_uploader(label="Upload your zip file", type=["zip"])
if uploaded_file is not None:
    print(uploaded_file.name)
    print(dir(uploaded_file))

def read_messages(uploaded_file):
    """Extracts zip file and convert message_1.json files into a single pandas dataframe
    """
    zipobj = ZipFile(uploaded_file, "r")
    zipobj.extractall()

    #Determine chat owner
    counter = Counter()
    for folder in os.listdir("messages/inbox"):
        with open(fr"messages/inbox/{folder}/message_1.json", "r") as json_file:
            data = json.load(json_file)
            counter.update(x["name"] for x in data["participants"])

    chat_owner = counter.most_common(1)[0][0].encode("latin1").decode("utf8")

    list_of_df = []
    for folder in os.listdir("messages/inbox"):
        with open(fr"messages/inbox/{folder}/message_1.json", "r") as json_file:
            data = json.load(json_file)

        df = pd.DataFrame(data["messages"])
        df["sender_name"] = df["sender_name"].apply(lambda x: x.encode("latin1").decode("utf8"))
        df["content"] = df["content"].apply(lambda x: str(x).encode("latin1").decode("utf8"))

        num_of_participants = len(data["participants"])
        if num_of_participants>2:
            # we have a group chat
            chat_name = folder.split("_")[0]
        else:
            # regular chat
            participants_list = df["sender_name"].unique().tolist()
            participants_list.remove(chat_owner)
            chat_name = participants_list[0]

        print(f"Proceessing {chat_name}'s messages")

        df["Chat"] = df["sender_name"].apply(lambda x: x if (x!=chat_owner) and (num_of_participants < 2) else chat_name)

        list_of_df.append(df)
    
    print("Changing timestamp_ms")
    complete_df = pd.concat(list_of_df, ignore_index=True)
    complete_df['timestamp_ms'] = pd.to_datetime(complete_df['timestamp_ms'], unit='ms')

    #Convert from UTC to local datetime
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()

    complete_df["timestamp_ms"] = complete_df["timestamp_ms"].apply(lambda x: x.replace(tzinfo=from_zone).astimezone(to_zone))
    complete_df.rename(columns={"timestamp_ms":"timestamp"})

    print("Computing char length")
    complete_df["char_length"] = complete_df['content'].str.len()

    print("Computing day of the week")
    complete_df["day_of_week"] = complete_df["timestamp_ms"].dt.dayofweek

    print("Computing hours")
    complete_df["hour"] = complete_df["timestamp_ms"].dt.hour

    print("Done :)")    
    return complete_df


if "df" not in st.session_state and uploaded_file is not None:
    st.session_state["df"] = read_messages(uploaded_file)
    print("Done loading session state")


if "df" in st.session_state:
    df = st.session_state["df"]

if uploaded_file is None:
    with header:
        st.title("Messenger Dashboard")
        st.markdown("How to generate the dashboard?")
        st.markdown("1. Go to facebook.com and go to the settings")
        st.markdown('2. Select "Your Facebook Information"')
        st.markdown('3. Then select "Download your information"')
        st.markdown("4. Select JSON format and Low media quality")
        st.markdown("5. Run prepare_zip.py script with --zip_path")
        st.code("python prepare_zip --zip_path facebook-yourUsername.zip", language="bash")
        st.markdown("6. Upload output_zip.zip in the sidebar")

if uploaded_file is not None:

    with dataset:
        st.header("Facebook inbox dataset")
        st.text("The data was obtained from Facebook by clicking Download your information.")
        st.markdown("If you want to use your own dataset, please read the instruction at following link")
        st.markdown(f"You have uploaded {uploaded_file}")
        
        msg_counts = df.groupby(["Chat", "sender_name"]).count().reset_index()
        figure = px.bar(msg_counts, x="Chat", y="char_length", color="sender_name", text_auto=True, width=1000, height=600)
        st.plotly_chart(figure)

        
        # Plot for one selected person
        option = st.selectbox("Choose your chat", df["Chat"].unique())

        st.write("You have chosen {}".format(option))

        selected_df = df[df["Chat"]==option].drop(columns=['Chat'])
        selected_df = selected_df.sort_values('timestamp_ms')[["sender_name","timestamp_ms", "content", "char_length"]]

        

        monthly = selected_df.groupby("sender_name").resample("M", on="timestamp_ms").sum().reset_index().sort_values(by="timestamp_ms")
        
        figure = px.line(monthly, x = "timestamp_ms", y="char_length", color="sender_name")
        st.plotly_chart(figure)


    with compare_two_chat_histories:
        
        chat1 = st.selectbox("Select the first chat for comparison", df["Chat"].unique())
        chat2 = st.selectbox("Select the second chat for comparison", df["Chat"].unique()) 

        selected_df = df[(df["Chat"]==chat1) | (df["Chat"]==chat2)]
        monthly = selected_df.groupby("Chat").resample("M", on="timestamp_ms").sum().reset_index().sort_values(by="timestamp_ms")

        figure = px.line(monthly, x = "timestamp_ms", y="char_length", color="Chat")
        st.plotly_chart(figure)

    with heatmap2d:

        selected_person = st.selectbox("Select the chat", df["Chat"].unique())
        del selected_df

        col1, col2 = st.columns(2)

        with col1:
            check_me = st.checkbox("Include my messages", True)
        with col2:
            check_other = st.checkbox(f"Include {selected_person}'s messages", True)

        selected_df = df[(df["Chat"]==selected_person)]
        who_am_i = Counter(df["sender_name"]).most_common(1)[0][0]

        if not check_me:
            selected_df = selected_df[selected_df["sender_name"] != who_am_i]

        if not check_other:
            selected_df = selected_df[selected_df["sender_name"] == who_am_i]
        
        figure = px.density_heatmap(selected_df, x="hour", y="day_of_week", nbinsx=12, text_auto=True)
        st.plotly_chart(figure)

    with wordcloud_countainer:
        st.header("Generate a wordcloud out of your text messages")
        
        selected_person = st.selectbox("Select the chat person", df["Chat"].unique())
        selected_df = df[(df["Chat"]==selected_person) & (df["content"].notnull())]["content"]
        
        stopwords = ["si", "sa", "ze", "tak", "som", "je", "nie", "ako", "na", "len", "v", 
                    "a", "to", "by", "co", "že", "do", "teda", "z", "iba"]
        wordcloud = WordCloud(stopwords=stopwords).generate("".join(selected_df.tolist()))

        #plt.imshow(wordcloud, interpolation="bilinear")
        #plt.axis("off")
        st.image(wordcloud.to_array(), width=700)



