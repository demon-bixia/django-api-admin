from django.utils.translation import gettext as _
from django_api_admin.sites import all_sites
from drf_spectacular.settings import spectacular_settings


def tag_paths(urls, endpoints, site, result, tag_name):
    for url in urls:
        for endpoint in endpoints:
            endpoint_url = site.url_prefix + endpoint[0]
            if result['paths'].get(endpoint_url, None):
                endpoint_url_path = endpoint[1][1:] if endpoint[1].startswith(
                    '/') else endpoint[1]
                if str(url.pattern) == endpoint_url_path and url.name != site.swagger_url_name:
                    for method, body in result['paths'][endpoint_url].items():
                        result['paths'][endpoint_url][method] = {
                            **body,
                            "tags": [tag_name]
                        }
    return result


def modify_schema(result, generator, request, public):
    # change the api info
    result['info'] = {
        'title': _('Django API Admin'),
        'description': _('A rewrite of django.contrib.admin as a Restful API, intended for use'
                         'in the process of creating custom admin panels using frontend frameworks like'
                         'react, and vue while maintaining an API similar to django.contrib.admin.'),
        'contact': 'msbizzacc0unt@gmail.com',
        'license': {
            'name': 'MIT License',
            'url': 'https://github.com/demon-bixia/django-api-admin/blob/production/LICENSE'
        },
        'version': "1.0.0",
    }

    # edit the tags for each path based on the model_admin or admin_site
    for site in all_sites:
        # create a generator and parse the site urls so that we can compare them below
        site_generator = spectacular_settings.DEFAULT_GENERATOR_CLASS(
            patterns=site.site_urls)
        site_generator.parse(request, True)
        result = tag_paths(
            site.site_urls,
            site_generator.endpoints,
            site,
            result,
            site.name
        )

        # update the urls for each registered model
        for model in site._registry.keys():
            model_urls = site.admin_urls.get(model, None)
            if model_urls:
                # create a generator and parse the admin urls so that we can compare them below
                admin_generator = spectacular_settings.DEFAULT_GENERATOR_CLASS(
                    patterns=model_urls)
                admin_generator.parse(request, True)
                result = tag_paths(
                    model_urls,
                    admin_generator.endpoints,
                    site,
                    result,
                    model._meta.verbose_name
                )

    return result
