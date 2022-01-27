import * as gesso from "./gesso.js";

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
      <div>Your name is <b id="name"></b>.</div>

      <form id="change-name-form" style="margin-bottom: 0;">
        <div class="form-field">
          <button type="submit">Change your name</button>
        </div>
      </form>

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

const helloTable = new gesso.Table("hello-table", [
    ["Frontend requests", "request"],
    ["Backend responses", "response"],
]);

export class MainPage extends gesso.Page {
    constructor(router) {
        super(router, "/", html);

        this.body.$("#hello-form").addEventListener("submit", event => {
            event.preventDefault();

            gesso.postJson("/api/say-hello", {
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

                this.router.navigate(new URL(`/?id=${data.id}`, window.location));
            });

            return;
        }

        super.process();
    }

    updateContent() {
        $("#name").textContent = this.name;

        gesso.getJson("/api/data", data => {
            const responses = Object.values(data).reverse();

            helloTable.update(responses, data);
        });
    }
}

export const router = new gesso.Router();

new MainPage(router);

new EventSource("/api/notifications").onmessage = event => {
    router.page.updateContent();
};
