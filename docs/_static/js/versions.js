document.addEventListener("DOMContentLoaded", function () {
  // Define known packages
  const PACKAGES = ["adk", "core", "langchain", "llamaindex"];

  // 1. Identify current version and package from URL
  const pathParts = window.location.pathname.split("/").filter((p) => p && p !== "index.html");


  let currentVersion = "latest"; // fallback
  let currentPackage = "core"; // fallback
  let versionIndex = -1;

  // Search for a package name in the path. The segment before it is likely the version.
  for (let i = 0; i < pathParts.length; i++) {
    if (PACKAGES.includes(pathParts[i])) {
      currentPackage = pathParts[i];
      if (i > 0) {
        currentVersion = pathParts[i - 1];
        versionIndex = i - 1;
      }
      break;
    }
  }

  // 2. Determine root path relative to current page

  let depth = 0;
  if (versionIndex !== -1) {
    depth = pathParts.length - versionIndex;
  }
  
  let rootPath = "";
  for(let i=0; i<depth; i++) {
      rootPath += "../";
  }

  if (rootPath === "") rootPath = "./";

  console.log(`Version: ${currentVersion}, Package: ${currentPackage}, Root: ${rootPath}`);

  fetch(rootPath + "versions.json")
    .then((r) => r.json())
    .then((versions) => {
      injectVersionMenu(versions, currentVersion, currentPackage, rootPath);
    })
    .catch((err) => console.error("Error loading versions.json:", err));
});

function injectVersionMenu(versions, currentVersion, currentPackage, rootPath) {
  const PACKAGES = ["adk", "core", "langchain", "llamaindex"];

  const container = document.createElement("div");
  container.className = "rst-versions";
  container.setAttribute("data-toggle", "rst-versions");
  container.setAttribute("role", "note");
  container.setAttribute("aria-label", "versions");

  // Display text
  container.innerHTML = `
    <span class="rst-current-version" data-toggle="rst-current-version">
      <span class="fa fa-book"></span>
      ${currentPackage} / ${currentVersion}
      <span class="fa fa-caret-down"></span>
    </span>
    <div class="rst-other-versions">
      <div style="text-align: left; padding-bottom: 10px;">
        <a href="${rootPath}index.html" style="color: #fcfcfc; text-decoration: none; font-weight: bold;">
          <span class="fa fa-home"></span> All Documentation
        </a>
      </div>
      <dl>
        <dt>Packages</dt>
        ${PACKAGES.map(
          (pkg) => `
          <dd${pkg === currentPackage ? ' class="current"' : ""}>
            <a href="${rootPath}${currentVersion}/${pkg}/index.html">${pkg}</a>
          </dd>`
        ).join("")}
      </dl>
      <dl>
        <dt>Versions</dt>
        ${versions.map(
          (v) => `
          <dd${v === currentVersion ? ' class="current"' : ""}>
            <a href="${rootPath}${v}/${currentPackage}/index.html">${v}</a>
          </dd>`
        ).join("")}
      </dl>
    </div>
  `;

  document.body.appendChild(container);
}
