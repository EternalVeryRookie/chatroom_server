import graphene


class Error(graphene.ObjectType):
    message = graphene.String()
    error_type = graphene.String()