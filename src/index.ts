import {
  JSONObject
} from '@phosphor/coreutils';

import {
  Widget
} from '@phosphor/widgets';

import {
  IRenderMime
} from '@jupyterlab/rendermime-interfaces';

import './browser-connector.js';

declare let MapdCon: any;

import '../style/index.css';

/**
 * The MIME type for backend-rendered MapD.
 */
export
const MIME_TYPE = 'application/vnd.mapd.vega+json';

/**
 * The MIME type for png data.
 */
export
const IMAGE_MIME = 'image/png';

/**
 * A class for rendering a MapD-generated image.
 */
export
class RenderedMapD extends Widget implements IRenderMime.IRenderer {
  constructor() {
    super();
    this._img = document.createElement('img');
    this.node.appendChild(this._img);
  }

  /**
   * Render MapD image into this widget's node.
   */
  renderModel(model: IRenderMime.IMimeModel): Promise<void> {
    let imageData = model.data[IMAGE_MIME] as string;
    if (imageData) {
      this._setImageData(imageData);
      return Promise.resolve(void 0);
    }

    const data = model.data[MIME_TYPE] as IMapDMimeBundle;
    const { connection, vega } = data;

    return new Promise<void>(resolve => {
      new MapdCon()
        .protocol(connection.protocol)
        .host(connection.host)
        .port(connection.port)
        .dbName(connection.dbname)
        .user(connection.user)
        .password(connection.password)
        .connect((error: any, con: any) => {
          con.renderVega(1, JSON.stringify(vega), {}, (error: any, result: any) => {
            if (error) {
              console.error(error.message);
            } else {
              model.setData({
                data: {
                  'image/png': result.image,
                  ...model.data
                },
                metadata: model.metadata
              });
              this._setImageData(result.image);
              resolve(void 0);
            }
          });
        });
    });
  }

  /**
   * Set the image data to a base64 encoded string.
   */
  private _setImageData(blob: string): void {
    let blobUrl = `data:${IMAGE_MIME};base64,${blob}`;
    this._img.src = blobUrl;
  }

  private _img: HTMLImageElement;
}

/**
 * Connection data for the mapd browser client.
 */
interface IMapDConnectionData extends JSONObject {
  host: string;
  protocol: string;
  port: string;
  user: string;
  dbname: string;
  password: string;
}

/**
 * MapD renderer custom mimetype format.
 */
interface IMapDMimeBundle extends JSONObject {
  connection: IMapDConnectionData;
  vega: JSONObject;
}

/**
 * A mime renderer factory for PDF data.
 */
export
const rendererFactory: IRenderMime.IRendererFactory = {
  safe: false,
  mimeTypes: [MIME_TYPE],
  defaultRank: 10,
  createRenderer: options => new RenderedMapD()
};


const extensions: IRenderMime.IExtension | IRenderMime.IExtension[] = [
  {
    id: 'jupyterlab-mapd:factory',
    rendererFactory,
    dataType: 'string',
  }
];

export default extensions;
