import os
import tarfile

from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from io import BytesIO, UnsupportedOperation

from debate.models import Debate
from argmining.models import ArgumentativeComponent, ArgumentativeRelation


class AnnFilesTarView(View):
    """
    View to get the brat annotated files for a debate.

    Given a debate identifier, this view builds the files for [brat standoff
    format](https://brat.nlplab.org/standoff.html), along with files for [brat
    configuration](https://brat.nlplab.org/configuration.html), so they can be
    setup within a brat server instance.

    The view is based on the code of
    [django-tarview](https://github.com/luckydonald/django-tarview), with some
    adaptations to ditch old Django versions compatibilities.
    """
    http_method_names = ["get"]

    def get_files(self) -> list[ContentFile]:
        """
        Builds the files to serve in the request:

        - annotation.conf: Brat Configuration for the Annotations.
        - tools.conf: Brat Configuration for the tools.
        - <debate_identifier>.txt: The text file with the whole debate, one line per statement.
        - <debate_identifier>.ann: The ann file with the components and relations.

        Returns a list of ``ContentFile`` with each of the files created.
        """
        debate = get_object_or_404(Debate, identifier=self.kwargs["identifier"])

        argumentative_component_labels = [
            choice[0] for choice in ArgumentativeComponent.ArgumentativeComponentLabel.choices
        ]
        argumentative_relation_labels = [
            choice[0] for choice in ArgumentativeRelation.ArgumentativeRelationLabel.choices
        ]
        annotation_config = ["[entities]"]
        annotation_config.extend(argumentative_component_labels)

        annotation_config.append("[relations]")
        for relation_label in argumentative_relation_labels:
            annotation_config.append(
                f"{relation_label}\t"
                f"Source:{'|'.join(argumentative_component_labels)}, "
                f"Target:{'|'.join(argumentative_component_labels)}"
            )

        annotation_config.extend(["[events]", "[attributes]"])
        annotation_config = ContentFile(
            "\n".join(annotation_config).encode("utf-8"), name="annotation.conf"
        )

        tools_config = [
            "[options]",
            "Validation\tvalidate:all",
            "Tokens\ttokenizer:whitespace",
            "Sentences\tsplitter:newline",  # This is particularly important to avoid brat splitting
            "Annotation-log\tlogfile:<NONE>",
        ]
        tools_config = ContentFile("\n".join(tools_config).encode("utf-8"), name="tools.conf")

        full_text = ""
        components = []

        for statement in debate.statements.order_by("pk"):
            offset = len(full_text)
            full_text += f"{statement.statement}\n"

            for component in statement.argumentative_components.order_by("pk"):
                components.append(
                    {
                        "id": f"T{component.identifier}",
                        "label": component.label,
                        "start": component.start + offset,
                        "end": component.end + offset,
                        "fragment": component.statement_fragment,
                    }
                )

        relevant_relations = ArgumentativeRelation.objects.filter(
            Q(source__statement__debate=debate) | Q(target__statement__debate=debate)
        )
        relations = []
        for ridx, relation in enumerate(relevant_relations, start=1):
            relations.append(
                {
                    "id": f"R{ridx}",
                    "label": relation.label,
                    "source": f"T{relation.source.identifier}",
                    "target": f"T{relation.target.identifier}",
                }
            )

        ann_file = [
            f"{comp['id']}\t{comp['label']} {comp['start']} {comp['end']}\t{comp['fragment']}"
            for comp in components
        ]
        ann_file += [
            f"{rel['id']}\t{rel['label']} Source:{rel['source']} Target:{rel['target']}"
            for rel in relations
        ]
        ann_file = ContentFile("\n".join(ann_file).encode("utf-8"), name=f"{debate.identifier}.ann")
        txt_file = ContentFile(full_text.encode("utf-8"), name=f"{debate.identifier}.txt")

        return [ann_file, txt_file, annotation_config, tools_config]

    def get(self, request, *args, **kwargs):
        """
        View to build the tarfile with the files for brat.

        The code is adapted from the original code in
        [django-tarview](https://github.com/luckydonald/django-tarview/blob/master/tarview/views.py)
        """
        tarfile_name = f"{self.kwargs['identifier']}.tgz"
        temp_file = ContentFile(b"", name=tarfile_name)
        with tarfile.TarFile(fileobj=temp_file, mode="w", debug=3) as tar_file:
            files = self.get_files()
            for file_ in files:
                file_name = file_.name
                try:
                    data = file_.read()
                except UnicodeDecodeError:
                    pass
                file_.seek(0, os.SEEK_SET)
                size = len(data)
                try:
                    if isinstance(data, bytes):
                        lol = BytesIO(data)
                    else:
                        lol = BytesIO(data.encode())
                except UnicodeDecodeError:
                    pass
                try:
                    info = tar_file.gettarinfo(fileobj=file_)
                except UnsupportedOperation:
                    info = tarfile.TarInfo(name=file_name)
                info.size = size
                tar_file.addfile(tarinfo=info, fileobj=lol)
        file_size = temp_file.tell()
        temp_file.seek(0)

        response = HttpResponse(temp_file, content_type="application/x-tar")
        response["Content-Disposition"] = f"attachment; filename={tarfile_name}"
        response["Content-Length"] = file_size
        return response
