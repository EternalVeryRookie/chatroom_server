import base64

from graphene.relay import Node


class UrlSafeEncodeNode(Node):

    class Meta:
        name = "UrlSafeEncodeNode"

    @classmethod
    def to_global_id(cls, type_, id):
        return base64.urlsafe_b64encode(f"{type_}:{id}".encode("utf-8")).decode('utf-8')

    @classmethod
    def from_global_id(cls, global_id):
        b64 = base64.urlsafe_b64decode(global_id).decode("utf-8")
        type_, id = b64.split(":")
        return type_, id

        