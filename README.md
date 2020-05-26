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

There are 2 types of organisations: Exporters and Chambers. They don't have much difference now and both can create documents.

There are 2 types of auth supported: username/password and remote identity provider. They should work more or less transparently (in the same manner).

The sign-up functionality is open, so anyone can create an account. The easiest approach is to create email/password one. But new accounts have no access to any organisation - thus can't see any data and can't create documents/etc. This is where custom human validation begins:

* it's either staff member manually adds new user to some organisation (implemented and working)
* or Identity Provided gives information about user's orgs (with govId for example)
* or the user who is already member of some organisation invites new users to that org (not implemented)

To follow the first method:

* Go to `Admin -> Users -> Organisations` section and ensure that desired organisation is created
* Go to `Admin -> Users -> Org Memberships` section and add a new one:
  * filling the org and the user
  * setting new user role

After that the new user should have access to the organisation (including objects created by another users of the same org).

### Document creation

After we have some user with the organisation access we can start to create documents. The base workflow is:

* Navigate to "Parties" section and add desired parties (exporters, importers, etc). Chambers app will probably add both these parties while exporters itself may be interested only in importers (or leave this section completely empty)
* Navigate to the Documents section and start document creation process
* Fill the form, upload some file
* Process by lodging the document and sending it to the Intergov upstream (node)
* Wait till the document is accepted by the node and it's status changed
* Wait for new updates from the remote parties
