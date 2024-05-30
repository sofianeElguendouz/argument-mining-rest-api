import os
import streamlit as st

from itertools import permutations
from streamlit_agraph import agraph, Config, Edge, Node
from transformers import pipeline
from text_highlighter import text_highlighter


LABELS = {"Premise": "NavajoWhite", "Claim": "PowderBlue"}
EXAMPLE = """
Well I welcome this opportunity to join Senator Kennedy completely on that statement and to say before this largest television audience in history something that I have been saying in the past and want to - will always say in the future. On our last television debate, I pointed out that it was my position that Americans must choose the best man that either party could produce. We can't settle for anything but the best. And that means, of course, the best man that this nation can produce. And that means that we can't have any test of religion. We can't have any test of race. It must be a test of a man. Also as far as religion is concerned. I have seen Communism abroad. I see what it does. Communism is the enemy of all religions; and we who do believe in God must join together. We must not be divided on this issue. The worst thing that I can think can happen in this campaign would be for it to be decided on religious issues. I obviously repudiate the Klan; I repudiate anybody who uses the religious issue; I will not tolerate it, I have ordered all of my people to have nothing to do with it and I say - say to this great audience, whoever may be listening, remember, if you believe in America, if you want America to set the right example to the world, that we cannot have religious or racial prejudice. We cannot have it in our hearts. But we certainly cannot have it in a presidential campaign.
""".strip()  # noqa


argumentative_components_pipeline = pipeline(
    task="token-classification",
    model="crscardellino/orbis-demo-seq-tag",
    token=os.getenv("HF_TOKEN"),
    aggregation_strategy="first",
)
argumentative_structure_pipeline = pipeline(
    task="text-classification",
    model="crscardellino/orbis-demo-rel-class",
    token=os.getenv("HF_TOKEN"),
)

st.set_page_config(layout="wide")

st.title("Argumentation Mining Demo")

st.subheader("Analyse Your Text")

fill_example = st.button("Run Example")

with st.form("argumentative-mining"):
    text = st.text_area("Argumentative Text Example:", value=EXAMPLE if fill_example else "")
    st.form_submit_button("Submit")

if text:
    st.subheader("Results")

    st.markdown("#### Visualization of the Argumentative Components")

    results = {"text": text}
    results["argumentative_components"] = [
        result for result in argumentative_components_pipeline(text) if result["score"] >= 0.75
    ]
    for argumentative_component in results["argumentative_components"]:
        argumentative_component["label"] = argumentative_component.pop("entity_group")
        argumentative_component["text"] = argumentative_component.pop("word")
        argumentative_component["id"] = hash(argumentative_component["text"])

    pair_indices = list(permutations(range(len(results["argumentative_components"])), 2))

    relations = argumentative_structure_pipeline(
        [
            {
                "text": results["argumentative_components"][i]["text"],
                "text_pair": results["argumentative_components"][j]["text"],
            }
            for i, j in pair_indices
        ]
    )
    results["argumentative_structure"] = []

    for rid, relation in enumerate(relations):
        if relation["label"] != "noRel" and relation["score"] >= 0.75:
            src, tgt = pair_indices[rid]
            results["argumentative_structure"].append(
                {
                    "source": results["argumentative_components"][src],
                    "target": results["argumentative_components"][tgt],
                    "label": relation["label"],
                    "score": relation["score"],
                }
            )

    highlighted_text = text_highlighter(
        text=text,
        labels=list(LABELS.items()),
        annotations=[
            {
                "start": argumentative_component["start"],
                "end": argumentative_component["end"],
                "tag": argumentative_component["label"],
            }
            for argumentative_component in results["argumentative_components"]
        ],
    )

    st.markdown("#### Visualization of the Argumentative Structure")
    nodes = []
    edges = []
    added_nodes = set()
    for relation in results["argumentative_structure"]:
        src = relation["source"]
        tgt = relation["target"]

        if src["id"] not in added_nodes:
            src_node = Node(
                id=src["id"],
                title=src["text"],
                label=src["label"],
                color=LABELS[src["label"]],
                shape="dot",
            )
            nodes.append(src_node)
            added_nodes.add(src["id"])

        if tgt["id"] not in added_nodes:
            tgt_node = Node(
                id=tgt["id"],
                title=tgt["text"],
                label=tgt["label"],
                color=LABELS[tgt["label"]],
                shape="dot",
            )
            nodes.append(tgt_node)
            added_nodes.add(tgt["id"])

        edge = Edge(
            source=src["id"],
            target=tgt["id"],
            color="green" if relation["label"] == "Support" else "red",
            label=relation["label"],
        )
        edges.append(edge)

    graph = agraph(nodes, edges, Config(physics=False, width=1500))

    st.markdown("#### Results in JSON")
    st.json(results, expanded=False)
