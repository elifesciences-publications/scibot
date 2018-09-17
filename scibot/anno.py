from collections import defaultdict
from h import models
from h.util.uri import normalize as uri_normalize
from h.models.document import update_document_metadata
from h.schemas.annotation import CreateAnnotationSchema
from pyontutils.utils import anyMembers
from IPython import embed

def uri_normalization(uri):
    """ NOTE: this does NOT produce uris """
    try:
        _, no_scheme = uri.split('://', 1)
        if anyMembers(no_scheme,
                      'acs.org',
                      'ahajournals.org',
                      'biologicalpsychiatryjournal.com',
                      'ebiomedicine.com',
                      'fasebj.org',
                      'frontiersin.org',
                      'future-science.com',
                      'hindawi.com',
                      'ieee.org',
                      'jclinepi.com',
                      'jpeds.com',
                      'liebertpub.com',
                      'mitpressjournals.org',
                      'molbiolcell.org',
                      'molmetab.com',
                      'neurobiologyofaging.org',
                      'physiology.org',
                      'sagepub.com',
                      'sciencedirect.com',
                      'tandfonline.com',
                      'theriojournal.com',
                      'wiley.com',):
            # NOTE not all the above hit all of these
            # almost all still resolve
            normalized = (no_scheme
                          .replace('/abstract', '')
                          .replace('/abs', '')
                          .replace('/full', '')
                          .replace('/pdf', ''))
        #elif ('sciencedirect.com' in no_scheme):
            #normalized = (no_scheme
                          #.replace('/abs', ''))
        elif ('cell.com' in no_scheme):
            normalized = (no_scheme  # FIXME
                          .replace('/abstract', '/XXX')
                          .replace('/fulltext', '/XXX'))
        elif 'jneurosci.org' in no_scheme:
            # TODO content/early -> resolution_chain(doi)
            normalized = (no_scheme
                          .replace('.short', '')
                          .replace('.full', '')
                          .replace('.pdf', '')
                          # note .full.pdf is a thing
                          )
        else:
            normalized = no_scheme
    except ValueError:  # split fail
        pdf_prefix = 'urn:x-pdf:'
        if uri.startswith(pdf_prefix):
            return uri
        else:
            raise TypeError(uri)

    return normalized


def disambiguate_uris(uris):
    bad = '/articles/6-124/v2', '//bmcbiol.biomedcentral.com/articles/10.1186/s12915-016-0257-2'
    dd = defaultdict(set)
    _ = [dd[uri_normalization(uri)].add(uri) for uri in uris if uri not in bad]
    return dict(dd)


class FakeRequest:
    def __init__(self, json):
        self.json = json
        self.authenticated_userid = json['user']


def validate(j):
    request = FakeRequest(j)
    schema = CreateAnnotationSchema(request)
    appstruct = schema.validate(j)
    return appstruct


def extract_extra(j):
    return j['id'], j['created'], j['updated']


def make_anno(data, dbdocs):
    #document_uri_dicts = data['document']['document_uri_dicts']
    #document_meta_dicts = data['document']['document_meta_dicts']
    #del data['document']
    #data = {k:v for k, v in data.items() if k != 'document'}  # prevent overwrite on batch load

    annotation = models.Annotation(**data)  # FIXME for batch the overhead here is stupid beyond belief
    annotation.document_id = dbdocs[uri_normalize(annotation.target_uri)].id
    #for k, v in data.items():
        #print(k, v)
        #setattr(annotation, k, v)
    #id, created, updated = extra
    #annotation.id = id
    #annotation.created = created
    #annotation.updated = updated

    return annotation

    # this baby is super slow
    document = update_document_metadata(
        session,
        annotation.target_uri,
        document_meta_dicts,
        document_uri_dicts,
        created=created,
        updated=updated)
    annotation.document = document

    return annotation


def quickload(j):
    """ a quickload routine for json that comes from the hypothes.is api
        and that has already passed the json schema validate checks """

    return {
        'id':j['id'],
        'created':j['created'],
        'updated':j['updated'],
        #'document':{},
        'extra':{},
        'groupid':j['group'],
        'references':j['references'] if 'references' in j else [],
        'shared':not j['hidden'] if 'hidden' in j else True,  # some time in august hidden was dropped
        'tags':j['tags'],
        'target_selectors':[selector
                            for selector_sources in j['target']
                            if 'selector' in selector_sources
                            for selector in selector_sources['selector']] ,
        'target_uri':j['uri'],  # FIXME check on this vs selectors
        'text':j['text'],
        'userid':j['user'],
    }


def doc(j):
    # FIXME this skips the normalize routines ...
    return {'document_meta_dicts': ([{'claimant': j['uri'],
                                      'type': 'title',  # FIXME see if more
                                      'value': j['document']['title']}]
                                    if 'title' in j['document']
                                    else []),
            'document_uri_dicts': [{'claimant': j['uri'],
                                    'content_type': '',  # FIXME see if more
                                    'type': 'self-claim',  # FIXME see if more
                                    'uri': j['uri']}]}


def mdoc(uri, claims):
    return {'document_meta_dicts': claims,
            'document_uri_dicts': [{'claimant': uri,
                                    'content_type': '',  # FIXME see if more
                                    'type': 'self-claim',  # FIXME see if more
                                    'uri': uri}]}


def add_doc_all(uri, created, updated, claims):  # batch only run once
    doc = models.Document(created=created, updated=updated)
    duri = models.DocumentURI(document=doc,  # how does this play out w/o creating explicitly?
                              claimant=uri,
                              uri=uri,
                              type='self-claim',
                              created=created,
                              updated=updated)
    #yield doc
    #yield duri
    for claim in claims:
        #yield
        models.DocumentMeta(document=doc,
                                  created=created,
                                  updated=updated,
                                  # FIXME for this we may need to pull the latest??? or no
                                  **claim)

    return doc


def quickuri(j):
    return (j['created'],
            j['updated'],
            [{'claimant':j['uri'], 'type':k, 'value':v}
             for k, v in j['document'].items()])