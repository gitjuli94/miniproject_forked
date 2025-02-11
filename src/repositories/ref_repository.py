from dataclasses import fields
from sqlalchemy import text
from entities.ref import Ref


def ref_from_row(row):
    return Ref(
        **{field.name: getattr(row, field.name, None) for field in fields(Ref)}
    )


def get_refs(db, **kwargs):
    """
    Fetches rows from the 'refs' table based on provided filter criteria. If no
    filters are specified, all rows are retrieved. Filters can be passed as
    named arguments (e.g., id=1, type='book'). The results are returned as
    a list of Ref objects, constructed dynamically by unpacking database rows.
    """

    valid_fields = [field.name for field in fields(Ref)]
    query_fields = ", ".join(valid_fields)

    query = f"SELECT {query_fields} FROM refs"

    conditions = []
    params = {}

    for field in valid_fields:
        if field in kwargs and kwargs[field] is not None:
            conditions.append(f"{field} = :{field}")
            params[field] = kwargs[field]

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    result = db.session.execute(text(query), params)
    refs = result.fetchall()

    return [ref_from_row(ref) for ref in refs]



def get_refs_tags(db, **kwargs):
    valid_fields = [field.name for field in fields(Ref)]
    query_fields = ", ".join([f"r.{field}" for field in valid_fields])

    query = f"""
    SELECT 
        {query_fields},
        COALESCE(json_agg(json_build_object('tag_name', t.tag_name)), '[]') AS tags
    FROM refs r
    LEFT JOIN ref_tags rt ON r.id = rt.ref_id
    LEFT JOIN tags t ON rt.tag_id = t.tag_id
    """

    conditions = []
    params = {}

    for field in valid_fields:
        if field in kwargs and kwargs[field] is not None:
            conditions.append(f"r.{field} = :{field}")
            params[field] = kwargs[field]

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY " + ", ".join([f"r.{field}" for field in valid_fields])

    result = db.session.execute(text(query), params)
    refs_with_tags = result.fetchall()

    return [
        {
            field.name: getattr(row, field.name, None) for field in fields(Ref)
        } | {"tags": row.tags}
        for row in refs_with_tags
    ]


def create_ref(db, ref: Ref):
    fields_to_insert = [
        field.name for field in fields(Ref)
        if getattr(ref, field.name) is not None]
    columns = ", ".join(fields_to_insert)
    placeholders = ", ".join([f":{field}" for field in fields_to_insert])

    sql = text(f"""
        INSERT INTO refs ({columns})
        VALUES ({placeholders})
    """)
    db.session.execute(sql, {
        field: getattr(ref, field) for field in fields_to_insert})
    db.session.commit()


def delete_ref(db, ref_id):
    sql = text("DELETE FROM refs WHERE id = :id")
    db.session.execute(sql, {"id": ref_id})
    db.session.commit()


def delete_all_refs(db):
    sql = text("TRUNCATE refs, ref_tags")
    db.session.execute(sql)
    db.session.commit()
