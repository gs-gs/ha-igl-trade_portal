from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from rest_framework import viewsets, mixins, generics
from rest_framework.response import Response

from trade_portal.documents.models import Document
from trade_portal.document_api.serializers import CertificateSerializer


class QsMixin(object):

    @cached_property
    def current_org(self):
        if getattr(self.request, "session", None):
            return self.request.user.get_current_org(self.request.session)
        else:
            # used in tests (currently), should be replaced by specifically
            # passing an "org" parameter for users with multiple orgs
            if len(self.request.user.direct_orgs) == 1:
                return self.request.user.direct_orgs[0]
            else:
                raise Exception("Please provide specific org for that request")

    def get_queryset(self):
        # note: this code is copied from the documents/views/documents.py
        # but will change in the future, having different filtering logic
        qs = Document.objects.all()
        if self.current_org.is_regulator:
            # regulator can see everything
            pass
        elif self.current_org.is_chambers:
            # chambers can see only their own documents
            qs = qs.filter(
                created_by_org=self.current_org
            )
        elif self.current_org.is_trader:
            qs = qs.filter(
                importer_name__in=(
                    self.current_org.name,
                    self.current_org.business_id,
                )
            ) | qs.filter(
                exporter__clear_business_id=self.current_org.business_id
            ).exclude(
                exporter__clear_business_id=""
            ) | qs.filter(
                exporter__name=self.current_org.name
            ).exclude(
                exporter__name=""
            )
        else:
            qs = Document.objects.none()

        qs = qs.select_related(
            "issuer", "exporter"
        )
        return qs

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])


class CertificateViewSet(QsMixin, viewsets.ViewSet, generics.ListCreateAPIView, mixins.UpdateModelMixin):
    queryset = Document.objects.all()

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        kwargs['user'] = self.request.user
        kwargs['org'] = self.current_org
        return CertificateSerializer(*args, **kwargs)

    # def list(self, request):
    #     # The only difference from the base list() procedure is providing a short serializer
    #     qs = self.get_queryset()
    #     page = self.paginate_queryset(qs)
    #     if page is not None:
    #         serializer = CertificateShortSerializer(page, many=True)
    #         return self.get_paginated_response(serializer.data)
    #     serializer = CertificateShortSerializer(qs, many=True)
    #     return Response(serializer.data)

    def retrieve(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    # def create(self, request):
    #     serializer = self.get_serializer(data=request.data, user=request.user)
    #     serializer.is_valid(raise_exception=True)
    #     obj = serializer.create()
    #     return Response(
    #         CertShortSerializer(obj).data,
    #         status=status.HTTP_201_CREATED,
    #     )


# class CertificateDetail(QsMixin, viewsets.ViewSet, generics.RetrieveUpdateAPIView):
#     queryset = Document.objects.all()

#     def get_serializer(self, *args, **kwargs):
#         kwargs['user'] = self.request.user
#         kwargs['org'] = self.request.user.get_current_org(self.request.session)
#         return CertificateSerializer(*args, **kwargs)