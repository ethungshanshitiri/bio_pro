# CV website for GitHub Pages

This is a single page CV style website built for GitHub Pages.

## Quick start

1. Create a new GitHub repository, for example ethungshan-cv
2. Upload all files from this folder into the repository root
3. In GitHub settings, open Pages and set Source to Deploy from a branch
4. Select branch main and folder root, then save

Your site will be available at the GitHub Pages URL for the repository.

## Update the profile links

Open js/main.js and set

- scholarProfileUrl
- orcidId

## Automatic publications updates

There are two options.

Option A recommended
Use ORCID public data. Set a repository secret named ORCID_ID with your ORCID identifier. If ORCID responds with 401, also set ORCID_TOKEN.

Option B experimental
Use Google Scholar. Set a repository secret named SCHOLAR_USER_ID. This relies on an unofficial client and may fail if Google Scholar rate limits or shows CAPTCHA.

The GitHub Actions workflow runs weekly and updates data/publications.json, then commits the change.

## Publications formatting and numbering

The page groups publications into Journals, Conferences, and Book chapters.

Numbering uses j, c, b with the latest publication having the largest number within each group.

## CV download button

The file assets/cv.pdf is served directly and the Download CV buttons use it.

Replace assets/cv.pdf with your newer CV PDF whenever you want.
