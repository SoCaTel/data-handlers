FROM node:10.13-alpine
# Set up Working Directory
WORKDIR /usr/src/app
# Copy Files that are needed for fetching the node modules
COPY ["package.json", "package-lock.json*",  "./"]
# Run npm install to fetch the new libraries
RUN npm install 
# Copy the rest of the files
COPY ./ ./
# Run the container's code
CMD node loader.js
