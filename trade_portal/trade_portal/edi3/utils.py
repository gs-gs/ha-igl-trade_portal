def party_from_json(json_data):
    from trade_portal.documents.models import Party

    issuer_id = json_data.get("id") or ""  # we call it issuer but it can be any party
    if ":" in issuer_id:
        issuer_bid_prefix, issuer_clear_business_id = issuer_id.rsplit(":", maxsplit=1)
    else:
        issuer_clear_business_id = issuer_id
        issuer_bid_prefix = ""
    the_party, _ = Party.objects.get_or_create(
        bid_prefix=issuer_bid_prefix,
        clear_business_id=issuer_clear_business_id,
        business_id=issuer_id,
        dot_separated_id=issuer_clear_business_id
        if "." in issuer_clear_business_id
        else "",
        name=json_data.get("name"),
        defaults={
            "country": json_data.get("postalAddress", {}).get("country") or "",
            "postcode": json_data.get("postalAddress", {}).get("postcode") or "",
            "countrySubDivisionName": json_data.get("postalAddress", {}).get(
                "postalAddress"
            )
            or "",
            "line1": json_data.get("postalAddress", {}).get("line1") or "",
            "line2": json_data.get("postalAddress", {}).get("line2") or "",
            "city_name": json_data.get("postalAddress", {}).get("cityName") or "",
        },
    )
    # TODO: update adresses if changed
    return the_party
