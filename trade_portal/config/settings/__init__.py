from environ import Env as EnvironEnv

from .kms import string_or_b64kms


class Env(EnvironEnv):
    """Extends environ.Env with added AWS KMS encryption support."""

    def __call__(self, var, cast=None,
                 default=EnvironEnv.NOTSET, parse_default=False):
        value = self.get_value(
            var, cast=cast,
            default=default, parse_default=parse_default
        )

        return string_or_b64kms(value)

    def db_url(self, var=EnvironEnv.DEFAULT_DATABASE_ENV, default=EnvironEnv.NOTSET, engine=None):
        """Returns a config dictionary, defaulting to DATABASE_URL.
        :rtype: dict
        """

        value = string_or_b64kms(self.get_value(var, default=default))

        return self.db_url_config(value, engine=engine)

    db = db_url
