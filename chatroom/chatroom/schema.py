import graphene

import users.schema
import chatapp.schema


class Query(users.schema.Query, chatapp.schema.Query, graphene.ObjectType):
    pass

class Mutation(users.schema.Mutation, chatapp.schema.Mutation, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)