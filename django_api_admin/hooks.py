from django_api_admin.sites import all_sites

# you could create a site_urls and admin_urls in the admin_site and model_admin classes
# then you could match each url with the urls in path and give them the appropriate tag


def modify_schema(result, generator, request, public):
    # change the api info
    result['info'] = {
        'title': 'Django API Admin',
        'description': 'A rewrite of django.contrib.admin as a Restful API, intended for use'
        'in the process of creating custom admin panels using frontend frameworks like'
        'react, and vue while maintaining an API similar to django.contrib.admin.',
        'contact': 'msbizzacc0unt@gmail.com',
        'license': {
            'name': 'MIT License',
            'url': 'https://github.com/demon-bixia/django-api-admin/blob/production/LICENSE'
        },
        'version': "1.0.0",
    }

    # edit the tags for each path based on the model_admin or admin_site
    # Note:
    # 1. if the urls are customized this way of generating the documentation must be changed
    # 2. if the app is customized so that two sites can have the same name
    #    this way of generating the documentation must be changed.

    # get the admin site name from the url that is the first part of the url
    admin_name = next(iter(result['paths'].keys())).strip('/').split('/')[0]
    # get the first matching admin site with the registered name
    site = next((site for site in all_sites if site.name == 'api_admin'), None)
    if site:
        # construct a list of the names of the registered models
        registered_models = {
            model._meta.verbose_name for model in site._registry.keys()}
        for url, path in result['paths'].items():
            params = url.strip('/').split('/')
            # if the model name is in the request url tag with the model name
            if len(params) > 2 and params[2] in registered_models:
                for method, body in path.items():
                    result['paths'][url][method] = {
                        **body, 'tags': [params[2]]
                    }
            else:
                # otherwise tag with the site name
                for method, body in path.items():
                    result['paths'][url][method] = {
                        **body, 'tags': [site.name]
                    }
    return result
