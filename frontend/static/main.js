import * as gesso from "./gesso/gesso.js";

const html = `
<body>
  <header>
    <div>
      <div>
        <span class="material-icons-outlined">emoji_people</span>
        Skupper Hello World
      </div>
    </div>
  </header>
  <section>
    <div>
      <div>Your name is <span id="name" class="name"></span>.</div>

      <form id="hello-form" style="margin-bottom: 2em;">
        <div class="form-field">
          <button type="submit">Say hello</button>
        </div>
      </form>

      <div id="hello-table"></div>
    </div>
  </section>
  <footer>
  </footer>
</body>
`;

function renderRequest(record, recordKey, context) {
    const elem = gesso.createElement(null, "div");

    elem.innerHTML = record.request.text.replace(record.request.name, `<span class="name">${record.request.name}</span>`);

    return elem;
}

function renderResponse(record, recordKey, context) {
    const elem = gesso.createElement(null, "div");

    if (record.error) {
        elem.innerHTML = `<span class="error">Error: ${record.error}</span>`;
    } else {
        elem.innerHTML = record.response.text.replace(record.response.name, `<span class="name">${record.response.name}</span>`);
    }

    return elem;
}

const helloTable = new gesso.Table("hello-table", [
    ["Frontend", "request", renderRequest],
    ["Backend", "response", renderResponse],
]);

class MainPage extends gesso.Page {
    constructor(router) {
        super(router, "/", html);

        this.body.$("#hello-form").addEventListener("submit", event => {
            event.preventDefault();

            gesso.postJson("/api/hello", {
                text: `Hello! I am ${this.name}.`,
                name: this.name,
            });
        });
    }

    process() {
        if (!this.id) {
            gesso.postJson("/api/generate-id", null, data => {
                this.id = data.id;
                this.name = data.name;

                super.process();
            });

            return;
        }

        super.process();
    }

    updateContent() {
        $("#name").textContent = this.name;

        gesso.getJson("/api/data", responseData => {
            const responses = Object.values(responseData).reverse();

            helloTable.update(responses, responseData);
        });
    }
}

const router = new gesso.Router();

new MainPage(router);

new EventSource("/api/notifications").onmessage = event => {
    router.page.updateContent();
};
