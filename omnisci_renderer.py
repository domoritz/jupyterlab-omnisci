""" Functions for backend rendering with OmniSci """

import ast
import base64
import uuid
import yaml

import vdom

try:
    import altair as alt
except ImportError:
    alt = None

from ipykernel.comm import Comm
from IPython.core.magic import register_cell_magic
from IPython.display import display
import IPython.display


class OmniSciBackendRenderer:
    """
    Class that produces a mimebundle that the notebook
    omnisci renderer can understand.
    """

    def __init__(self, connection, data=None, vl_data=None):
        """
        Initialize the backend renderer. Either `data` or `vl_data`
        is required.

        Parameters
        =========

        connection: dict
            A dictionary containing the connection data for the omnisci
            server. Must include 'user', 'password', 'host', 'port',
            'dbname', and 'protocol'

        data: dict
            Vega data to render.
        
        data: dict
            Vega lite data to render.
        """
        if (not (data or vl_data)) or (data and vl_data):
            raise RuntimeError("Either vega or vega lite data must be specified")
        self.connection = connection
        self.data = data
        self.vl_data = vl_data

    def _repr_mimebundle_(self, include=None, exclude=None):
        """
        Return a mimebundle with 'application/vnd.omnisci.vega+json'
        data, which is a custom mimetype for rendering omnisci vega
        in Jupyter notebooks.
        """
        bundle = {"connection": self.connection}
        if self.data:
            bundle["vega"] = self.data
        else:
            bundle["vegalite"] = self.vl_data
        return {"application/vnd.omnisci.vega+json": bundle}


def render_vega(connection, vega):
    _widget_count = 1
    nonce = str(uuid.uuid1())
    result = connection._client.render_vega(
        connection._session, _widget_count, vega, 1, nonce
    )
    data = base64.b64encode(result.image).decode()
    return vdom.img([], src=f"data:image/png;base64,{data}")


@register_cell_magic
def omnisci(line, cell):
    """
    Cell magic for rendering vega produced by the omnisci backend.

    Usage: Initiate it with the line `%% omnisci $connection_data`,
    where `connection_data` is the dictionary containing the connection
    data for the OmniSci server. The rest of the cell should be yaml-specified
    vega data.
    """
    connection_data = ast.literal_eval(line)
    vega = yaml.load(cell)
    display(OmniSciBackendRenderer(connection_data, vega))


@register_cell_magic
def omnisci_vl(line, cell):
    """
    Cell magic for rendering vega lite produced by the omnisci backend.

    Usage: Initiate it with the line `%% omnisci $connection_data`,
    where `connection_data` is the dictionary containing the connection
    data for the OmniSci server. The rest of the cell should be yaml-specified
    vega lite data.
    """
    connection_data = ast.literal_eval(line)
    vl = yaml.load(cell)
    display(OmniSciBackendRenderer(connection_data, vl_data=vl))


def omnisci_mimetype(spec, conn):
    """
    Returns a omnisci vega lite mimetype, assuming that the URL
    for the vega spec is actually the SQL query
    """
    data = spec["data"]
    data["sql"] = data.pop("url")
    return {
        "application/vnd.omnisci.vega+json": {
            "vegalite": spec,
            "connection": {
                "host": conn.host,
                "protocol": conn.protocol,
                "port": conn.port,
                "user": conn.user,
                "dbName": conn.db_name,
                "password": conn.password,
            },
        }
    }


if alt:
    alt.renderers.register("omnisci", omnisci_mimetype)


COMM_ID = "extract-vega-lite"


def extract_spec(spec, callback):

    my_comm = Comm(target_name=COMM_ID, data=spec)

    @my_comm.on_msg
    def _recv(msg):
        callback(msg["content"]["data"])


class VegaLite(IPython.display.DisplayObject):
    def _repr_mimebundle_(self, include, exclude):
        from altair.vegalite.v2.display import default_renderer

        return default_renderer(self.data)


EMPTY_SPEC = {"data": {"values": []}, "mark": "bar"}


def display_vega_lite_extracted(spec: VegaLite):
    display_id = display(VegaLite(EMPTY_SPEC), display_id=True)
    extract_spec(spec.data, lambda s: display_id.update(VegaLite(s)))
