# ArcGIS Server Service Publisher

**Note: This is a work in progress!**

Publishes MXD files to Map Services on ArcGIS Server using [YAML](https://en.wikipedia.org/wiki/YAML) configuration files.

MXD files are matched based on the names of the services, for example `CouncilDistrictsFill` maps to `CouncilDistrictsFill.mxd`.

By default, configuration files are looked for in the `./config` subdirectory, and logs are written to `./logs`.

Configuration files must have a `.yml` extension.

You create one configuration file per service folder -- each service folder can contain many services.

You must also create a `userconfig.yml` file specifying the properties (URL, token, and path to ArcGIS Server connection file) for each of your server instances.

### Requirements

  - Windows 7+
  - ArcGIS Desktop 10.3+
  - Python 2.7+
  - [pip](https://pip.pypa.io/en/stable/installing/)
  - [PyYAML](https://pypi.python.org/pypi/PyYAML) 3.11 (will be installed by pip as described in the Setup Instructions)

### Setup Instructions

  - Clone this repository to a local directory
  - Open a Windows command prompt in the local directory
  - Type `pip install -r requirements.txt`
  - Create a folder named `config` in the local directory
  - Create a file named `userconfig.yml` in the `config` folder, and populate it with a key named `ags_instances` containing a mapping of ArcGIS Server instance names and the following properties:
    - `url`: Base URL (scheme and hostname) of your ArcGIS Server instance
    - `token`: ArcGIS Admin REST API token (see the [example usage section](#example-usage) below for more details.)
    - `ags_connection`: Path to an `.ags` connection file for each instance.
  - Create additional configuration files for each service folder you want to publish.
  - See the [example configuration files](#example-configuration-files) section below for more details.

### Example configuration files

 - `CouncilDistrictMap.yml`

    ``` yml
    service_folder: CouncilDistrictMap
    services:
      - CouncilDistrictMap
      - CouncilDistrictsFill
    default_service_properties:
      isolation: low
      instances_per_container: 8
    environments:
      dev:
        ags_instances:
          - coagisd1
          - coagisd2
        mxd_dir: \\coacd.org\gis\AGS\Config\AgsEntDev\mxd-source\CouncilDistrictMap
      test:
        ags_instances:
          - coagist1
          - coagist2
        data_source_mappings:
          \\coacd.org\gis\AGS\Config\AgsEntDev\Service-Connections\gisDmDev (COUNCILDISTRICTMAP_SERVICE).sde: \\coacd.org\gis\AGS\Config\AgsEntTest\Service-Connections\gisDmTest (COUNCILDISTRICTMAP_SERVICE).sde
          \\coacd.org\gis\AGS\Config\AgsEntDev\Service-Connections\gisDmDev (COUNCILDISTRICTMAP_SERVICE) external.sde: \\coacd.org\gis\AGS\Config\AgsEntTest\Service-Connections\gisDmTest (COUNCILDISTRICTMAP_SERVICE) external.sde
        mxd_dir: \\coacd.org\gis\AGS\Config\AgsEntTest\mxd-source\CouncilDistrictMap
        mxd_dir_to_copy_from: \\coacd.org\gis\AGS\Config\AgsEntDev\mxd-source\CouncilDistrictMap
      prod:
        ags_instances:
          - coagisp1
          - coagisp2
        data_source_mappings:
          \\coacd.org\gis\AGS\Config\AgsEntTest\Service-Connections\gisDmTest (COUNCILDISTRICTMAP_SERVICE).sde: \\coacd.org\gis\AGS\Config\AgsEntProd\Service-Connections\gisDm (COUNCILDISTRICTMAP_SERVICE).sde
          \\coacd.org\gis\AGS\Config\AgsEntTest\Service-Connections\gisDmTest (COUNCILDISTRICTMAP_SERVICE) external.sde: \\coacd.org\gis\AGS\Config\AgsEntProd\Service-Connections\gisDm (COUNCILDISTRICTMAP_SERVICE) external.sde
        mxd_dir: \\coacd.org\gis\AGS\Config\AgsEntProd\mxd-source\CouncilDistrictMap
        mxd_dir_to_copy_from: \\coacd.org\gis\AGS\Config\AgsEntTest\mxd-source\CouncilDistrictMap
    ```

 - `userconfig.yml`

    ``` yml
    ags_instances:
      coagisd1:
        url: http://coagisd1.austintexas.gov
        token: <token obtained from ags_utils.generate_token>
        ags_connection: C:\Users\pughl\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\coagisd1-pughl (admin).ags
      coagisd2:
        url: http://coagisd2.austintexas.gov
        token: <token obtained from ags_utils.generate_token>
        ags_connection: C:\Users\pughl\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\coagisd2-pughl (admin).ags
      coagist1:
        url: http://coagist1.austintexas.gov
        token: <token obtained from ags_utils.generate_token>
        ags_connection: C:\Users\pughl\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\coagist1-pughl (admin).ags
      coagist2:
        url: http://coagist2.austintexas.gov
        token: <token obtained from ags_utils.generate_token>
        ags_connection: C:\Users\pughl\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\coagist2-pughl (admin).ags
      coagisp1:
        url: http://coagisp1.austintexas.gov
        token: <token obtained from ags_utils.generate_token>
        ags_connection: C:\Users\pughl\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\coagisp1-pughl (admin).ags
      coagisp2:
        url: http://coagisp2.austintexas.gov
        token: <token obtained from ags_utils.generate_token>
        ags_connection: C:\Users\pughl\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\coagisp2-pughl (admin).ags
    ```

### Example Usage

1. Publish the `dev` environment in the `./config/CouncilDistrictMap.yml` configuration file:

    ```
    python -c "import runner; runner.run_batch_publishing_job(['CouncilDistrictMap'], included_envs=['dev'])"
    ```
2. Publish all **except** for the `dev` environment (e.g. `test` and `prod`) using `excluded_envs`:

    ```
    python -c "import runner; runner.run_batch_publishing_job(['CouncilDistrictMap'], excluded_envs=['dev'])"
    ```
3. Publish all the environments in the `./config/CouncilDistrictMap.yml` configuration file (e.g., `dev`, `test`, and `prod`), but only publish the `CouncilDistrictsFill` service:

    ```
    python -c "import runner; runner.run_batch_publishing_job(['CouncilDistrictMap'], included_services=['CouncilDistrictsFill'])"
    ```
  - **Tip:** You can use [`fnmatch`](https://docs.python.org/2/library/fnmatch.html)-style wildcards in any of the strings in the arguments to `run_batch_publishing_job`, so you could put `included_services=['CouncilDistrict*']` and both `CouncilDistrictMap` and `CouncilDistrictsFill` would be published.

4. Clean up any services that have not been defined in the `./config/CouncilDistrictMap.yml` configuration file:

   ```
   python -c "import runner; runner.run_batch_cleanup_job(['CouncilDistrictMap'])
   ```
5. Generate an ArcGIS Admin REST API token for an ArcGIS Server instance named `coagisd1` that expires in 30 days:

   ```
   python -c "import ags_utils; print ags_utils.generate_token('coagisd1', expiration='43200')"
   ```
   - **Tip:**  Copy and paste the generated token into `userconfig.yml` as the value for the `token` key corresponding to the ArcGIS server instance it was generated on.


### TODO

- Create a nicer command line interface
- Support other types of services
- Probably lots of other stuff
