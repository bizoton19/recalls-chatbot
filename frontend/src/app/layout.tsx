import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CPSC Recalls | Consumer Product Safety Commission",
  description:
    "Search consumer product recalls from the U.S. Consumer Product Safety Commission. Find recalls, hazards, and remedies using our AI-powered assistant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link
          rel="stylesheet"
          href="https://unpkg.com/@uswds/uswds@3.11.0/dist/css/uswds.min.css"
        />
      </head>
      <body>
        {/* Skip navigation */}
        <a className="usa-skipnav" href="#main-content">
          Skip to main content
        </a>

        {/* Official government banner */}
        <section
          className="usa-banner"
          aria-label="Official website of the United States government"
        >
          <div className="usa-accordion">
            <header className="usa-banner__header">
              <div className="usa-banner__inner">
                <div className="grid-col-auto">
                  <img
                    aria-hidden="true"
                    className="usa-banner__header-flag"
                    src="https://unpkg.com/@uswds/uswds@3.11.0/dist/img/us_flag_small.png"
                    alt=""
                  />
                </div>
                <div className="grid-col-fill tablet:grid-col-auto">
                  <p className="usa-banner__header-text">
                    An official website of the United States government
                  </p>
                  <p className="usa-banner__header-action" aria-hidden="true">
                    Here&apos;s how you know
                  </p>
                </div>
                <button
                  type="button"
                  className="usa-accordion__button usa-banner__button"
                  aria-expanded="false"
                  aria-controls="gov-banner-default"
                >
                  <span className="usa-banner__button-text">Here&apos;s how you know</span>
                </button>
              </div>
            </header>
            <div
              className="usa-banner__content usa-accordion__content"
              id="gov-banner-default"
              hidden
            >
              <div className="grid-row grid-gap-lg">
                <div className="usa-banner__guidance tablet:grid-col-6">
                  <img
                    className="usa-banner__icon usa-media-block__img"
                    src="https://unpkg.com/@uswds/uswds@3.11.0/dist/img/icon-dot-gov.svg"
                    role="img"
                    alt=""
                    aria-hidden="true"
                  />
                  <div className="usa-media-block__body">
                    <p>
                      <strong>Official websites use .gov</strong>
                      <br />A <strong>.gov</strong> website belongs to an official government
                      organization in the United States.
                    </p>
                  </div>
                </div>
                <div className="usa-banner__guidance tablet:grid-col-6">
                  <img
                    className="usa-banner__icon usa-media-block__img"
                    src="https://unpkg.com/@uswds/uswds@3.11.0/dist/img/icon-https.svg"
                    role="img"
                    alt=""
                    aria-hidden="true"
                  />
                  <div className="usa-media-block__body">
                    <p>
                      <strong>Secure .gov websites use HTTPS</strong>
                      <br />A <strong>lock</strong> or <strong>https://</strong> means you&apos;ve
                      safely connected to the .gov website.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Site header */}
        <header className="usa-header usa-header--basic" role="banner">
          <div className="usa-nav-container">
            <div className="usa-navbar">
              <div className="usa-logo">
                <em className="usa-logo__text">
                  <a href="/" title="CPSC Recalls Home" aria-label="CPSC Recalls — Home">
                    <span style={{ color: "#005288", fontWeight: 700 }}>CPSC</span>
                    <span style={{ color: "#1b1b1b" }}> Recalls</span>
                  </a>
                </em>
              </div>
            </div>
            <nav aria-label="Primary navigation" className="usa-nav">
              <ul className="usa-nav__primary usa-accordion">
                <li className="usa-nav__primary-item">
                  <a href="/" className="usa-nav__link">
                    <span>Latest Recalls</span>
                  </a>
                </li>
                <li className="usa-nav__primary-item">
                  <a href="/search" className="usa-nav__link">
                    <span>Image Search</span>
                  </a>
                </li>
                <li className="usa-nav__primary-item">
                  <a href="/chat" className="usa-nav__link">
                    <span>Ask the Assistant</span>
                  </a>
                </li>
                <li className="usa-nav__primary-item">
                  <a
                    href="https://www.saferproducts.gov"
                    className="usa-nav__link"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span>SaferProducts.gov</span>
                  </a>
                </li>
              </ul>
            </nav>
          </div>
        </header>

        <main id="main-content">{children}</main>

        {/* Footer */}
        <footer className="usa-footer usa-footer--slim">
          <div className="usa-footer__primary-section">
            <div className="usa-footer__primary-container grid-row">
              <div className="mobile-lg:grid-col-8">
                <nav className="usa-footer__nav" aria-label="Footer navigation">
                  <ul className="grid-row grid-gap">
                    <li className="mobile-lg:grid-col-6 desktop:grid-col-auto usa-footer__primary-content">
                      <a className="usa-footer__primary-link" href="https://www.cpsc.gov/Recalls">
                        All CPSC Recalls
                      </a>
                    </li>
                    <li className="mobile-lg:grid-col-6 desktop:grid-col-auto usa-footer__primary-content">
                      <a className="usa-footer__primary-link" href="https://www.saferproducts.gov">
                        Report a Safety Problem
                      </a>
                    </li>
                    <li className="mobile-lg:grid-col-6 desktop:grid-col-auto usa-footer__primary-content">
                      <a className="usa-footer__primary-link" href="https://www.cpsc.gov/about-cpsc/contact-information">
                        Contact CPSC
                      </a>
                    </li>
                  </ul>
                </nav>
              </div>
            </div>
          </div>
          <div className="usa-footer__secondary-section">
            <div className="grid-container">
              <div className="usa-footer__logo grid-row grid-gap-2">
                <div className="grid-col-auto">
                  <p className="usa-footer__logo-heading">U.S. Consumer Product Safety Commission</p>
                  <p className="usa-footer__logo-tagline">
                    Hotline: <a href="tel:800-638-2772">800-638-2772</a> &bull;{" "}
                    <a href="https://www.cpsc.gov/privacy-policy">Privacy Policy</a> &bull;{" "}
                    <a href="https://www.cpsc.gov/about-cpsc/accessibility-statement">Accessibility</a>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </footer>

        {/* USWDS JS */}
        <script
          src="https://unpkg.com/@uswds/uswds@3.11.0/dist/js/uswds-init.min.js"
          async
        />
        <script
          src="https://unpkg.com/@uswds/uswds@3.11.0/dist/js/uswds.min.js"
          async
        />
      </body>
    </html>
  );
}
