import base64

from graphene.relay import Node


class UrlSafeEncodeNode(Node):

    class Meta:
        name = "UrlSafeEncodeNode"

    @staticmethod
    def to_global_id(type_, id):
        return base64.urlsafe_b64encode(f"{type_}:{id}".encode("utf-8")).decode('utf-8')

    @staticmethod
    def get_node_from_global_id(info, global_id, only_type=None):
        type_, id = base64.urlsafe_b64decode(global_id).split(":")
        if only_type:
            # We assure that the node type that we want to retrieve
            # is the same that was indicated in the field type
            assert type_ == only_type._meta.name, "Received not compatible node."

        return type_, id
        