from typing import Callable

from graphql.error.base import GraphQLError


def reraise_graphql_error(func: Callable):
    """
    GraphQLのresolverがロジック実行中に例外をcatchした際に、それをGraphQLErrorに変換してreraiseする
    """
    def resolver(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            raise GraphQLError(str(err)) from err

    return resolver
