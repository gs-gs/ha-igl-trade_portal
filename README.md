# Trade Portal

The "Trade Portal" demonstrates how a Customs Authority may use the
intergov to facilitate exports.

The app uses an external identity provider, to simulate integration
with a national exporter identification scheme. The registration is available to anyone, but admin actions need to be performed so freshly registered users
have required permissions. In the real world the authentication mechanism
will provide all required information.

For detailed technical documentation and development details, see the `DEV.md` file.

## Usage

### User roles and permission

The Trade UI supports multiple organisations working at the same time without affecting each other, and each organisation may have multiple users working on the same data. Each user of the organisation has access to any object for that org.

There are 3 types of organisations: Traders (exporters and importers), Chambers (organisations which can create documents and send them) and Regulators (readonly access to everything).

There are 2 types of auth supported: username/password and remote identity provider. They should work more or less transparently (in the same manner).

The sign-up functionality is open, so anyone can create an account. The easiest approach is to create email/password one. But new accounts have no access to any organisation - thus can't see any data and can't create documents/etc. This is where custom human validation begins:

* it's either staff member manually adds new user to some organisation (navigate to `/admin/users/orgmembership/add/` and create a new object)
* or Identity Provided gives information about user's orgs (with govId for example) - not implemented yet
* or the user who is already member of some organisation invites new users to that org (not implemented as well)

### Document creation

After we have some user with the organisation access we can start to create documents. The base workflow is:

* Navigate to "Parties" section and add desired parties (exporters, importers, etc). Chambers app will probably add both these parties while exporters itself may be interested only in importers (or leave this section completely empty)
* Navigate to the Documents section and start document creation process
* Fill the form, upload some file
* Process by lodging the document and sending it to the Intergov upstream (node)
* Wait till the document is accepted by the node and it's status changed
* Wait for new updates from the remote parties


### Translations

We use https://django-amazon-translate.readthedocs.io/en/latest/installation.html library
to ask AWS Translate to make the translations for us. It saves times, but the translations
can look dumb in some places. Although it's easy to fix the most irritating ones manually.

To update them:

* pip install django_amazon_translate
* add `django_amazon_translate` line to the base.py, INSTALLED_APPS
* export your AWS credentials with AWS Translate access to env variables
* ./manage.py auto_translate_text
* ./manage.py compilemessages
* restart the web container
* ensure it's working
* remove `django_amazon_translate` from the INSTALLED_APPS

Please note this dependency and code changes is not pushed to the master because
it's rare manual operation anyway.
